import streamlit as st
from dotenv import load_dotenv
load_dotenv()
import whisperx
import openai
import os
import json
import re
import pandas as pd
from opencc import OpenCC

# --- 导入自定义工具包 ---
from utils.metrics import calculate_wpm, generate_radar_chart
from utils.rag_engine import process_jd_to_context
from utils.db_manager import save_interview_result, get_last_interview, get_all_history, init_db

cc = OpenCC('t2s')

# --- 1. 初始化阶段 ---
st.set_page_config(page_title="AI 面试复盘助手", layout="wide", page_icon="🎤")
init_db() # 初始化数据库/打印云端连接状态

# 模拟用户 ID (SaaS 核心)
current_user_id = "user_01" 

# 初始化 Session State 防止报错
if 'report' not in st.session_state: st.session_state.report = None
if 'transcript' not in st.session_state: st.session_state.transcript = None
if 'df_wpm' not in st.session_state: st.session_state.df_wpm = None
if 'scores' not in st.session_state: st.session_state.scores = None

# 辅助函数：解析 AI 报告中的 JSON 分数
def extract_scores(text):
    try:
        match = re.search(r'Scores:\s*(\{.*?\})', text, re.DOTALL)
        if match: return json.loads(match.group(1))
    except Exception as e:
        print(f"解析分数失败: {e}")
    return None

# --- 2. UI 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("火山引擎 API Key", type="password", value=os.getenv("VOLC_API_KEY", ""))
    endpoint_id = st.text_input("豆包接入点 ID (EP-ID)", value=os.getenv("DOUBAO_ENDPOINT_ID", ""))
    model_size = st.selectbox("Whisper 模型", ["tiny", "base", "small"], index=0)

    st.divider()
    st.header("🎯 岗位针对性增强")
    jd_file = st.file_uploader("上传目标岗位 JD (PDF/TXT)", type=['pdf', 'txt'])

# --- 3. 主界面布局 ---
st.title("🎤 AI 面试复盘助手")
uploaded_file = st.file_uploader("选择面试视频文件", type=["mp4", "mkv", "mov", "avi"])

# 定义 4 个标签页
tab_video, tab_metrics, tab_report, tab_history = st.tabs(["🎥 视频处理", "📊 量化分析看板", "🧠 AI 深度诊断", "📈 成长轨迹"])

video_path = "temp_video.mp4"

with tab_video:
    if uploaded_file:
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.video(video_path)
    else:
        st.info("请先上传视频文件")

# --- 4. 执行复盘逻辑 ---
if st.button("🚀 开始一键复盘", type="primary"):
    if not api_key or not endpoint_id:
        st.error("请先在左侧配置 API Key 和 接入点 ID！")
    elif not uploaded_file:
        st.error("请先上传面试视频！")
    else:
        with st.status("正在进行深度分析...", expanded=True) as status:
            # A. 处理 JD (RAG 环节)
            jd_context = "通用面试评价标准"
            if jd_file:
                st.write("正在检索岗位核心要求...")
                temp_jd = f"temp_{jd_file.name}"
                with open(temp_jd, "wb") as f: f.write(jd_file.getvalue())
                jd_context = process_jd_to_context(temp_jd)
                os.remove(temp_jd)

            # B. 获取历史记录用于对比 (SaaS 核心逻辑)
            st.write("正在提取历史表现以进行对比分析...")
            last_record = get_last_interview(current_user_id)
            comparison_context = ""
            if last_record:
                ls = last_record.get('scores', {})
                comparison_context = f"\n【该用户历史表现】：上次语速 {last_record.get('avg_wpm')} WPM，技术评分 {ls.get('技术深度', 'N/A')}。"

            # C. 转录与对齐
            st.write("正在转录音频（WhisperX）...")
            device = "cpu"
            model = whisperx.load_model(model_size, device, compute_type="int8")
            audio = whisperx.load_audio(video_path)
            result = model.transcribe(audio, batch_size=16, language="zh")
            
            st.write("正在校准时间戳并计算指标...")
            model_a, metadata = whisperx.load_align_model(language_code="zh", device=device)
            aligned_result = whisperx.align(result["segments"], model_a, metadata, audio, device)
            
            # D. 量化计算
            df_wpm = calculate_wpm(aligned_result["segments"])
            full_transcript = ""
            for segment in aligned_result["segments"]:
                full_transcript += f"[{segment['start']:.2f}s] {cc.convert(segment['text'])}\n"
            
            # E. AI 分析 (升级 Prompt 增加对比)
            st.write("正在呼叫豆包 AI 生成定制化复盘报告...")
            client = openai.OpenAI(api_key=api_key, base_url="https://ark.cn-beijing.volces.com/api/v3")
            
            prompt = f"""
            你是一个资深面试官。请参考[岗位要求]评估本次[面试文本]。
            {comparison_context}
            
            任务：
            1. 诊断技术点与逻辑。
            2. 给出“成长对比”：对比历史表现（若有），分析是否有进步。
            3. 结尾包含 JSON 评分 Scores: {{"技术深度": 8, "逻辑表达": 7, "自信度": 9, "沟通技巧": 8, "岗位匹配度": 7}}
            
            [岗位要求]: {jd_context}
            [面试文本]: {full_transcript}
            """
            
            response = client.chat.completions.create(model=endpoint_id, messages=[{"role": "user", "content": prompt}])
            coach_feedback = response.choices[0].message.content
            
            # F. 更新状态
            st.session_state.df_wpm = df_wpm
            st.session_state.scores = extract_scores(coach_feedback)
            st.session_state.report = coach_feedback
            st.session_state.transcript = full_transcript

            # G. ✨ 同步到数据库
            try:
                save_interview_result(
                    avg_wpm=float(df_wpm['wpm'].mean()) if not df_wpm.empty else 0,
                    scores=st.session_state.scores,
                    report=coach_feedback,
                    transcript=full_transcript,
                    user_id=current_user_id
                )
                st.toast("✅ 数据已同步至云端/本地数据库", icon="💾")
            except Exception as e:
                st.error(f"数据库写入失败: {e}")
                 
            status.update(label="复盘完成！", state="complete", expanded=False)

# --- 5. 结果展示区 ---
if st.session_state.report:
    with tab_metrics:
        st.subheader("📊 面试表现量化看板")
        col1, col2 = st.columns(2)
        with col1:
            st.write("📈 语速波动曲线 (WPM)")
            st.line_chart(st.session_state.df_wpm.set_index('start')['wpm'])
            st.download_button("📥 下载语速原始数据 (CSV)", data=st.session_state.df_wpm.to_csv(index=False).encode('utf-8'), file_name="wpm_data.csv")
            
        with col2:
            st.write("🕸️ 能力画像雷达图")
            if st.session_state.scores:
                fig = generate_radar_chart(st.session_state.scores)
                st.plotly_chart(fig, use_container_width=True)

    with tab_report:
        st.subheader("🤖 AI 教练深度复盘报告")
        st.download_button("📥 下载 Markdown 复盘报告", data=st.session_state.report, file_name="analysis.md")
        st.markdown(st.session_state.report)
        st.divider()
        st.subheader("📝 详细转录文本")
        st.download_button("📥 下载详细转录文本 (TXT)", data=st.session_state.transcript, file_name="transcript.txt")
        st.text_area("内容", st.session_state.transcript, height=400)

with tab_history:
    st.subheader("🚀 你的面试进化史")
    history_data = get_all_history(current_user_id)
    
    if not history_data:
        st.info("暂无历史数据，去完成你的第一次面试吧！")
    else:
        # 转换数据用于绘图 (兼容 SQL/Supabase 返回格式)
        h_dates = [d[0] for d in history_data]
        h_wpms = [d[1] for d in history_data]
        
        st.write("📊 语速平稳度趋势")
        st.line_chart(pd.DataFrame({"语速 (WPM)": h_wpms}, index=h_dates))
        
        st.write("📈 核心维度得分走势")
        score_list = []
        for d in history_data:
            s_dict = d[2] if isinstance(d[2], dict) else json.loads(d[2])
            s_dict['日期'] = d[0]
            score_list.append(s_dict)
        
        st.line_chart(pd.DataFrame(score_list).set_index('日期'))