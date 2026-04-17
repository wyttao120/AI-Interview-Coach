import os
import gc
import whisperx
import openai
import json
import re
from opencc import OpenCC
from dotenv import load_dotenv

# --- 1. 导入工具函数 (确保同步 SaaS 功能) ---
from utils.metrics import calculate_wpm
from utils.rag_engine import process_jd_to_context
# 新增：云端数据库管理
from utils.db_manager import save_interview_result, get_last_interview

# 加载环境变量
load_dotenv()

VOLC_API_KEY = os.getenv("VOLC_API_KEY")
DOUBAO_ENDPOINT_ID = os.getenv("DOUBAO_ENDPOINT_ID")

if not VOLC_API_KEY or not DOUBAO_ENDPOINT_ID:
    print("❌ 错误：请检查 .env 文件配置")
    exit()

# 项目参数
video_file = "interview.mp4" 
current_user_id = "user_01"  # 模拟用户 ID
device = "cpu" 
batch_size = 16 
compute_type = "int8" 
cc = OpenCC('t2s')

# --- 2. 增强型 AI 分析函数 ---
def ai_coach_analyze(text, jd_context="通用标准", last_record=None):
    print("\n--- 正在呼叫 豆包 AI 进行 SaaS 级深度分析 ---")
    
    # 构建对比背景
    comparison_context = ""
    if last_record:
        ls = last_record.get('scores', {})
        comparison_context = f"""
        【该用户历史表现回顾】：
        - 上次平均语速：{last_record.get('avg_wpm')} WPM
        - 上次评分：技术深度({ls.get('技术深度', '无')}), 逻辑表达({ls.get('逻辑表达', '无')})
        请在分析时重点对比本次面试是否有进步。
        """

    client = openai.OpenAI(api_key=VOLC_API_KEY, base_url="https://ark.cn-beijing.volces.com/api/v3")
    
    prompt = f"""
    你是一个资深面试官。请结合[岗位要求]评估本次[面试文本]。
    {comparison_context}
    
    任务：
    1. 诊断技术点与逻辑。
    2. 给出“成长对比”：对比历史表现，分析其语速稳定性、技术深度等维度的变化。
    3. 结尾包含 JSON 评分 Scores: {{"技术深度": 8, "逻辑表达": 7, "自信度": 9, "沟通技巧": 8, "岗位匹配度": 7}}
    
    [岗位要求]: {jd_context}
    [面试文本]: {text}
    """
    
    try:
        response = client.chat.completions.create(
            model=DOUBAO_ENDPOINT_ID,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 分析失败: {str(e)}"

# --- 3. 运行 WhisperX 流程 ---
print("--- 正在加载模型并进行语音识别 ---")
model = whisperx.load_model("tiny", device, compute_type=compute_type)
audio = whisperx.load_audio(video_file)
result = model.transcribe(audio, batch_size=batch_size, language="zh")

print("--- 正在校准时间戳 ---")
model_a, metadata = whisperx.load_align_model(language_code="zh", device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device)

# --- 4. SaaS 逻辑：获取历史记录 ---
print(f"--- 正在连接 Supabase 获取用户 {current_user_id} 的历史数据 ---")
last_record = get_last_interview(current_user_id)

# --- 5. 指标计算与 AI 诊断 ---
# A. 处理 JD
jd_path = "target_jd.txt" 
jd_context = process_jd_to_context(jd_path) if os.path.exists(jd_path) else "通用面试标准"

# B. 计算语速 WPM
df_wpm = calculate_wpm(result["segments"])
avg_wpm = float(df_wpm['wpm'].mean()) if not df_wpm.empty else 0

# C. 整理文本
full_transcript = "".join([f"[{s['start']:.2f}s] {cc.convert(s['text'])}\n" for s in result["segments"]])

# D. AI 对比分析
coach_feedback = ai_coach_analyze(full_transcript, jd_context, last_record)

# E. 解析评分
scores = {}
score_match = re.search(r'Scores:\s*(\{.*?\})', coach_feedback, re.DOTALL)
if score_match:
    scores = json.loads(score_match.group(1))

# --- 6. ✨ 核心更新：同步到云端数据库 ---
print("--- 正在同步复盘数据至云端数据库 ---")
try:
    save_interview_result(
        avg_wpm=avg_wpm,
        scores=scores,
        report=coach_feedback,
        transcript=full_transcript,
        user_id=current_user_id
    )
    print("✅ 云端同步成功！")
except Exception as e:
    print(f"❌ 数据库写入失败: {e}")

# --- 7. 保存本地 Markdown 报告 ---
report_file = "interview_report.md"
with open(report_file, "w", encoding="utf-8") as f:
    f.write(f"# 🎧 AI 智能面试复盘报告\n\n## 📊 核心指标\n- **平均语速**: {avg_wpm:.1f} WPM\n")
    if scores:
        f.write(f"- **多维评分**: {scores}\n")
    f.write(f"\n## 🤖 AI 教练诊断\n{coach_feedback}\n")
    f.write(f"\n---\n## 📝 详细转录\n```text\n{full_transcript}\n```")

print(f"\n--- ✅ 任务完成！报告已生成：{report_file} ---")