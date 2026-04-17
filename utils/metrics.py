import pandas as pd
import plotly.graph_objects as go
import re

def calculate_wpm(segments):
    """
    【核心函数】计算每段语速 (WPM)，兼容中英混排
    """
    data = []
    for seg in segments:
        # 确保数据中有 start 和 end 字段
        start_time = seg.get('start', 0)
        end_time = seg.get('end', 0)
        text = seg.get('text', "").strip()
        
        duration_sec = end_time - start_time
        duration_min = duration_sec / 60
        
        # 过滤掉时长过短的片段（通常是呼吸音或杂音）
        if duration_min > 0.008: 
            # 1. 清洗数据：去除标点符号
            clean_text = re.sub(r'[^\w\s]', '', text)
            
            # 2. 计算长度：判断是中文还是英文
            if re.search(r'[\u4e00-\u9fa5]', clean_text):
                count = len(clean_text) # 中文按字数计
            else:
                count = len(clean_text.split()) # 英文按单词数计
            
            wpm = count / duration_min
            
            # 限制异常值
            if wpm < 500: 
                data.append({
                    "start": round(start_time, 2), 
                    "wpm": round(wpm, 1), 
                    "text": text
                })
                
    return pd.DataFrame(data)

def generate_radar_chart(scores):
    """
    生成五维雷达图
    """
    if not scores:
        return None
        
    categories = list(scores.keys())
    values = list(scores.values())

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name='面试表现'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        showlegend=False
    )
    return fig