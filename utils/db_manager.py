import os
import openai
from dotenv import load_dotenv # 新增
from supabase import create_client, Client
load_dotenv() # 新增：确保无论谁调用我，我都能先加载环境变量

# 1. 初始化客户端
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
if not url or not key:
    raise ValueError("错误：无法从 .env 文件读取 SUPABASE_URL 或 SUPABASE_KEY，请检查文件内容！")

supabase: Client = create_client(url, key)

def init_db():
    """
    云端数据库无需在代码里 init，你需要在 Supabase 的 SQL Editor 里手动建表。
    这里可以留空或写一个打印调试信息。
    """
    print("☁️ 使用 Supabase 云端数据库模式")

def save_interview_result(avg_wpm, scores, report, transcript, user_id="default_user"):
    """
    保存面试数据到 Supabase（保持函数名一致，方便 app.py 调用）
    """
    data = {
        "user_id": user_id,
        "avg_wpm": avg_wpm,
        "scores": scores,
        "report": report,
        "transcript": transcript
    }
    try:
        response = supabase.table("interviews").insert(data).execute()
        return response
    except Exception as e:
        print(f"❌ Supabase 写入失败: {e}")
        return None

def get_last_interview(user_id="default_user"):
    """获取该用户最近一次记录"""
    try:
        response = supabase.table("interviews") \
            .select("avg_wpm, scores, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        return response.data[0] if response.data else None
    except:
        return None

def get_all_history(user_id="default_user"):
    """获取所有历史，用于画成长曲线"""
    try:
        response = supabase.table("interviews") \
            .select("created_at, avg_wpm, scores") \
            .eq("user_id", user_id) \
            .order("created_at", desc=False) \
            .execute()
        # 转换格式以匹配之前的绘图逻辑
        return [(d['created_at'], d['avg_wpm'], d['scores']) for d in response.data]
    except:
        return []
def get_user_profile(user_id="default_user"):
    """
    提取用户的长期画像：从历史数据中计算平均分趋势
    """
    # 1. 直接复用已有的历史查询函数
    history = get_all_history(user_id)
    
    # 2. 只有一条记录或没记录时，判定为新用户
    if not history or len(history) < 2:
        return "该用户为新用户，暂无长期历史数据。"

    # 3. 提取最近最多 5 次的技术深度得分 (d[2] 是 scores 字典)
    # 这里的 history 是按时间升序排列的，所以取最后 5 个
    recent_records = history[-5:]
    recent_scores = [
        d[2].get('技术深度', 0) if isinstance(d[2], dict) else 0 
        for d in recent_records
    ]
    
    avg_score = sum(recent_scores) / len(recent_scores)
    
    return f"用户近期 {len(recent_scores)} 次面试技术平均分：{avg_score:.1f}。历史关注点：语速稳定性、技术表达的连贯性。"

# utils/db_manager.py 增加以下内容

def get_history_fragments(user_id="default_user", limit=2):
    """
    【非向量化版本】直接按时间顺序读取最近 N 次面试的转录文本片段
    """
    try:
        response = supabase.table("interviews") \
            .select("transcript, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        if not response.data:
            return "（暂无历史面试片段）"
        
        fragments = []
        for item in response.data:
            date_str = item['created_at'][:10]
            # 截取前 400 字，既能给 AI 提供细节，又不会爆 Token
            text_snippet = item['transcript'][:400] 
            fragments.append(f"--- 历史面试记录 ({date_str}) ---\n{text_snippet}...")
            
        return "\n\n".join(fragments)
    except Exception as e:
        print(f"读取历史片段失败: {e}")
        return "（无法读取历史面试细节）"