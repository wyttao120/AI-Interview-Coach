import os
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