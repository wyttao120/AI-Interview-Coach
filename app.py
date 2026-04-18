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
from utils.db_manager import save_interview_result, get_last_interview, get_all_history, init_db

# --- 导入自定义工具包 ---
from utils.metrics import calculate_wpm, generate_radar_chart
from utils.rag_engine import process_jd_to_context

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
if 'jd_context' not in st.session_state: st.session_state.jd_context = "通用面试评价标准"
if 'cv_context' not in st.session_state: st.session_state.cv_context = "暂无简历信息"
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "我是你的 AI 面试导师，你可以针对本次面试复盘向我提问，或让我帮你练习特定环节。"}]

# 辅助函数：解析 AI 报告中的 JSON 分数
def extract_scores(text):
    try:
        match = re.search(r'Scores:\s*(\{.*?\})', text, re.DOTALL)
        if match: 
            return json.loads(match.group(1))
    except Exception as e:
        st.error(f"解析分数失败: {e}") # 建议在前端报错，方便调试
    return None

# --- 2. UI 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("火山引擎 API Key", type="password", value=os.getenv("VOLC_API_KEY", ""))
    endpoint_id = st.text_input("豆包接入点 ID (EP-ID)", value=os.getenv("DOUBAO_ENDPOINT_ID", ""))
    model_size = st.selectbox("Whisper 模型", ["tiny", "base", "small"], index=0)

    st.divider()
    st.header("🎯 岗位针对性增强")
    jd_file = st.file_uploader("上传目标岗位 JD (图片/PDF/TXT)", type=['pdf', 'txt', 'png', 'jpg', 'jpeg'])
    st.header("📄 个人背景增强")
    cv_file = st.file_uploader("上传个人简历 (图片/PDF/TXT)", type=['pdf', 'txt', 'png', 'jpg', 'jpeg'])

# --- 3. 主界面布局 ---
st.title("🎤 AI 面试复盘助手")
uploaded_file = st.file_uploader("选择面试视频文件", type=["mp4", "mkv", "mov", "avi"])

# 定义 4 个标签页
tab_video, tab_metrics, tab_report, tab_history, tab_assistant = st.tabs(["🎥 视频处理", "📊 量化分析看板", "🧠 AI 深度诊断", "📈 成长轨迹", "💬 AI 助手"])

video_path = "temp_video.mp4"

with tab_history:
    st.subheader("🚀 你的面试进化史")
    try:
        history_data = get_all_history(current_user_id)
        if not history_data:
            st.info("👋 欢迎新同学！你还没有历史面试数据，完成复盘后这里将生成成长曲线。")
        else:
            st.success(f"📊 已加载共计 {len(history_data)} 次面试记录。")
            # ... 后续绘图逻辑 ...
    except Exception as e:
        st.error(f"历史档案加载失败: {e}")

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
                st.write(f"🔍 正在解析上传的 JD 文件: {jd_file.name}...")
                temp_jd = f"temp_{jd_file.name}"
                with open(temp_jd, "wb") as f: 
                    f.write(jd_file.getvalue())
                
                # 调用解析函数
                jd_context = process_jd_to_context(temp_jd)
                os.remove(temp_jd) # 清理临时文件

                # --- 新增诊断反馈逻辑 ---
                if not jd_context or jd_context == "通用面试评价标准":
                    st.warning("⚠️ 岗位 JD 解析结果似乎为空。如果上传的是图片，请确认：\n1. 图片文字是否清晰；\n2. 您的接入点 ID 是否支持 Vision (视觉) 模型。")
                else:
                    st.info(f"✅ JD 解析成功！识别到约 {len(jd_context)} 个字符。")

# --- 新增：处理个人简历 (Resume 环节) ---
            cv_context = st.session_state.cv_context # 默认值
            if cv_file:
                st.write(f"📄 正在解析上传的简历: {cv_file.name}...")
                temp_cv = f"temp_cv_{cv_file.name}"
                with open(temp_cv, "wb") as f:
                    f.write(cv_file.getvalue())
                
                # 直接复用你已有的 process_jd_to_context，因为它支持多种格式
                cv_context = process_jd_to_context(temp_cv)
                os.remove(temp_cv) 
                st.session_state.cv_context = cv_context # 更新到 session_state
                st.info(f"✅ 简历解析成功！")

            # B. 获取历史记录用于对比 (SaaS 核心逻辑)
            st.write("正在提取历史表现以进行对比分析...")
            comparison_context = ""
            
            try:
                # 调用数据库函数获取最后一次记录
                last_record = get_last_interview(current_user_id)
                
                if last_record:
                    # 成功获取到数据
                    ls = last_record.get('scores', {})
                    last_date = last_record.get('created_at', '')[:10] # 截取日期
                    
                    # 在 UI 上展示一个小反馈
                    st.success(f"✅ 已成功调取历史档案 (最近一次: {last_date})")
                    
                    comparison_context = f"\n【该用户历史表现】：上次语速 {last_record.get('avg_wpm')} WPM，技术评分 {ls.get('技术深度', 'N/A')}。"
                else:
                    # 数据库返回空（新用户）
                    st.write("ℹ️ 暂无历史记录，本次将作为您的首次面试档案。")
            except Exception as e:
                # 网络或数据库配置报错
                st.error(f"❌ 无法连接云端历史库: {e}")

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
            你是一个资深面试官。请参考[岗位要求]和[个人简历]评估本次[面试文本]。
            {comparison_context}
            
            任务：
            1. 诊断技术点与逻辑。
            2. 给出“成长对比”：对比历史表现（若有），分析是否有进步。
            3. ✨ 新增“简历 vs 表现”差异分析：对比[个人简历]，指出用户有哪些简历中的亮点在本次面试中被忽略了，或哪些表达与简历不符。
            4. 结尾包含 JSON 评分 Scores: {{"技术深度": 分数, "逻辑表达":  分数, "自信度":  分数, "沟通技巧":  分数, "岗位匹配度":  分数}}
            
            [岗位要求]: {jd_context}
            [个人简历]: {st.session_state.cv_context}
            [面试文本]: {full_transcript}
            """
            
            response = client.chat.completions.create(model=endpoint_id, messages=[{"role": "user", "content": prompt}])
            coach_feedback = response.choices[0].message.content
            
            # F. 更新状态
            st.session_state.df_wpm = df_wpm
            st.session_state.scores = extract_scores(coach_feedback)
            st.session_state.report = coach_feedback
            st.session_state.transcript = full_transcript
            st.session_state.jd_context = jd_context

            # G. ✨ 同步到数据库
            try:
                # 确保你已经从 utils.db_manager 导入了 save_interview_result
                save_interview_result(
                    avg_wpm=float(df_wpm['wpm'].mean()) if not df_wpm.empty else 0,
                    scores=st.session_state.scores,
                    report=coach_feedback,
                    transcript=full_transcript,
                    user_id=current_user_id
                )
                st.toast("✅ 数据已同步至云端", icon="💾")
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
                st.plotly_chart(fig, width="stretch")
            else:
                st.warning("⚠️ AI 报告格式不符合预期，未能提取到量化评分。")

    with tab_report:
        st.subheader("🤖 AI 教练深度复盘报告")
        if "简历" in st.session_state.report:
            st.info("💡 本次报告已包含简历对比分析，请查看‘简历 vs 表现’章节。")
        st.markdown(st.session_state.report)
        st.download_button("📥 下载 Markdown 复盘报告", data=st.session_state.report, file_name="analysis.md")
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

# ✨ 新增：在此处插入第二张图的代码 (建议补全 AI 调用逻辑)
with tab_assistant:
    st.write("### 💬 AI 面试导师")
    # 1. 展示对话历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 2. 用户提问逻辑
    if user_query := st.chat_input("针对复盘结果向我提问..."):
        # 将用户消息存入 Session State 并展示
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # 3. 调用 AI 助手（带上下文）
        with st.chat_message("assistant"):
            if st.session_state.report:
                from utils.db_manager import get_user_profile, get_history_fragments
                
                with st.spinner("正在调取历史面试档案..."):
                    # 1. 获取分数趋势（画像）
                    user_long_term_profile = get_user_profile(current_user_id)
                    # 2. 获取最近面试的对话原文（非向量化）
                    mem_context = get_history_fragments(current_user_id)
                    print("\n--- 正在调取历史记忆片段 ---")

                    if "暂无" in mem_context:
                        print("⚠️ 提示：未检测到可回溯的对话片段。")
                    else:
                        print(f"✅ 成功调取历史片段，共计约 {len(mem_context)} 字符。")

                api_messages = [
                    {
                        "role": "system", 
                        "content": f"""你是一个拥有长期记忆的面试导师。
                        【历史面试原话片段】：
                        {mem_context}
                        
                        【用户长期得分画像】：{user_long_term_profile}
                        【当前岗位要求】：{st.session_state.get('jd_context')}
                        【用户个人简历】：{st.session_state.get('cv_context')}
                        【本次复盘报告】：{st.session_state.report}
                        
                        任务：请结合上述所有背景。如果历史面试片段与用户当前问题相关，请进行对比辅导。"""
                    }
                ]
                # 加上之前的聊天记录（注意：跳过第一条欢迎语以节省 Token）
                api_messages.extend(st.session_state.messages[-10:])
                
                client = openai.OpenAI(api_key=api_key, base_url="https://ark.cn-beijing.volces.com/api/v3")
                res = client.chat.completions.create(
                    model=endpoint_id,
                    messages=api_messages # 👈 传入完整的对话链
                )
                
                full_res = res.choices[0].message.content
                st.markdown(full_res)
                # 3. 把 AI 的回答也存入记忆
                st.session_state.messages.append({"role": "assistant", "content": full_res})
            else:
                st.info("💡 请先在‘视频处理’标签页完成一次面试复盘，以便我结合你的具体表现提供指导。")