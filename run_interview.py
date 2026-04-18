import os
import gc
import whisperx
import openai
import json
import re
import pandas as pd
from opencc import OpenCC
from dotenv import load_dotenv

# --- 1. 导入工具函数 (确保同步 SaaS 功能) ---
from utils.metrics import calculate_wpm
from utils.rag_engine import process_jd_to_context
# 新增：云端数据库管理
from utils.db_manager import save_interview_result, get_last_interview, get_user_profile, get_history_fragments

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
def ai_coach_analyze(text, jd_context="通用标准", cv_context="暂无简历", last_record=None):
    print("\n--- 正在呼叫 豆包 AI 进行深度复盘分析 ---")
    
    # 构建对比背景
    comparison_context = ""
    if last_record:
        ls = last_record.get('scores', {})
        comparison_context = f"\n【该用户历史表现】：上次平均语速 {last_record.get('avg_wpm')} WPM，技术评分 {ls.get('技术深度', 'N/A')}。"

    client = openai.OpenAI(api_key=VOLC_API_KEY, base_url="https://ark.cn-beijing.volces.com/api/v3")
    
    prompt = f"""
    你是一个资深面试官。请结合[岗位要求]和[个人简历]评估本次[面试文本]。
    {comparison_context}
    
            任务：
            1. 诊断技术点与逻辑。
            2. 给出“成长对比”：对比历史表现（若有），分析是否有进步。
            3. ✨ 新增“简历 vs 表现”差异分析：对比[个人简历]，指出用户有哪些简历中的亮点在本次面试中被忽略了，或哪些表达与简历不符。
            4. 结尾包含 JSON 评分 Scores: {{"技术深度": 分数, "逻辑表达":  分数, "自信度":  分数, "沟通技巧":  分数, "岗位匹配度":  分数}}
            
            [岗位要求]: {jd_context}
            [个人简历]: {cv_context}
            [面试文本]: {full_transcript}
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

try:
    last_record = get_last_interview(current_user_id)
    
    # ✨ 新增判断逻辑
    if last_record:
        # 获取成功且有数据
        print(f"✅ 历史记录获取成功！最后一次面试时间: {last_record.get('created_at', '未知')}")
        print(f"📈 上次得分：{last_record.get('scores', {})}")
    else:
        # 连接正常但该用户数据库里是空的
        print("ℹ️ 提示：未找到该用户的历史记录（新用户），将按首次面试进行分析。")
except Exception as e:
    # 彻底连接失败（如网络问题、Key 错误）
    print(f"❌ 警告：连接 Supabase 失败，无法获取历史数据。错误信息: {e}")
    last_record = None # 确保程序不会因为变量未定义而崩溃

# --- 5. 指标计算与 AI 诊断 ---
# A. 处理 JD
jd_files = ["target_jd.txt", "target_jd.png", "target_jd.jpg", "target_jd.pdf"]
# 寻找目录下第一个存在的文件
jd_path = next((f for f in jd_files if os.path.exists(f)), None)
if jd_path:
    print(f"检测到 JD 文件: {jd_path}, 正在解析...")
    jd_context = process_jd_to_context(jd_path)
    if not jd_context or jd_context == "通用面试标准":
        print("⚠️ 警告：JD 解析结果为空，请检查图片是否清晰或模型是否支持 Vision。")
else:
    print("ℹ️ 未检测到 target_jd 文件，将使用通用面试标准。")
print(f"🔍 调试：读取到的 JD 内容长度为 {len(jd_context)}，内容摘要：{jd_context[:50]}...")

cv_files = ["target_cv.txt", "target_cv.png", "target_cv.jpg", "target_cv.pdf"]
cv_path = next((f for f in cv_files if os.path.exists(f)), None)
cv_context = process_jd_to_context(cv_path) if cv_path else "暂无简历信息"
print(f"📄 简历解析状态: {'已加载' if cv_path else '未检测到简历'}")

# B. 计算语速 WPM
df_wpm = calculate_wpm(result["segments"])
avg_wpm = float(df_wpm['wpm'].mean()) if not df_wpm.empty else 0

# C. 整理文本
full_transcript = "".join([f"[{s['start']:.2f}s] {cc.convert(s['text'])}\n" for s in result["segments"]])

# D. AI 对比分析
# 获取该用户在 Supabase 的最后一次复盘数据
last_record = get_last_interview(current_user_id)
coach_feedback = ai_coach_analyze(full_transcript, jd_context, cv_context, last_record)

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

# --- 8. ✨ 新增：交互式命令行 AI 导师 ---
user_profile = get_user_profile(current_user_id)
history_mems = get_history_fragments(current_user_id)
print("\n--- 正在调取历史记忆片段 ---")
history_mems = get_history_fragments(current_user_id)

if "暂无" in history_mems:
    print("⚠️ 提示：未检测到可回溯的对话片段。")
else:
    print(f"✅ 成功调取历史片段，共计约 {len(history_mems)} 字符。")

chat_history = [
    {
        "role": "system", 
        "content": f"""你是一个拥有长期记忆的面试导师。
        【历史面试原话片段】：{history_mems}
        【用户长期得分画像】：{user_profile}
        【目标岗位要求】：{jd_context}
        【个人简历内容】：{cv_context}
        【本次复盘报告】：{coach_feedback}

        任务：结合以上所有背景。如果历史片段相关，请进行对比辅导。
        """
    }
]

print("\n" + "="*30)
print("💬 进入 AI 导师互动模式 (输入 'q' 退出)")
print("="*30)

while True:
    user_input = input("\n👤 你: ")
    if user_input.lower() in ['q', 'quit', 'exit']:
        break
        
    # --- 步骤 2：将用户输入存入对话历史 ---
    chat_history.append({"role": "user", "content": user_input})
    
    client = openai.OpenAI(api_key=VOLC_API_KEY, base_url="https://ark.cn-beijing.volces.com/api/v3")
    try:
        # --- 步骤 3：调用 API 时，使用 messages=chat_history ---
        # 这样 AI 就能看到之前所有的对话记录，而不只是当前这一个问题
        res = client.chat.completions.create(
            model=DOUBAO_ENDPOINT_ID,
            messages=chat_history 
        )
        
        answer = res.choices[0].message.content
        print(f"\n🤖 AI 导师: {answer}")
        
        # --- 步骤 4：获取 AI 回复后，同样存入列表 ---
        # 这样下次你提问时，AI 才知道它刚才对你说了什么
        chat_history.append({"role": "assistant", "content": answer})
        
    except Exception as e:
        print(f"❌ 对话出错: {e}")

print("\n👋 祝你面试顺利，再见！")