# 🛡️ AI Interview Coach (SaaS 版 AI 面试复盘助手)

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Framework-Streamlit-red.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/Database-Supabase-blueviolet.svg)](https://supabase.com/)

> **从录像到量化成长：基于 SaaS 架构的全栈 AI 面试复盘专家，助你攻克技术大厂。**

本项目是一款集成了 **WhisperX 高精度转录**、**RAG 岗位针对性诊断**以及 **Supabase 云端历史追踪** 的全自动化面试复盘工具。它不仅能诊断单次面试，更能通过长期记忆系统追踪你的成长曲线。

---

## ✨ 核心特性

* **⚡ 高精度语音对齐**：集成 `WhisperX`，实现字级别的精准时间戳标注与 ASR 转录。
* **🎯 岗位针对性增强 (RAG)**：支持上传目标岗位 JD，通过 **LangChain** 检索增强生成技术，实现“一岗一策”的精准诊断。
* **📈 长期成长轨迹 (Long-term Memory)**：
* **数据持久化**：集成 **Supabase (PostgreSQL)**，面试记录云端同步。
* **进化看板**：自动比对历次面试得分，生成语速平稳度、技术得分走势图。
* **🤖 豆包 Pro 深度诊断**：基于火山引擎大模型，提供 5 维度量化评分：
* **技术深度**：评估知识点覆盖的广度与深度。
* **逻辑表达**：诊断回答是否有条理、是否简洁。
* **岗位匹配**：分析回答与 JD 要求的契合度。
* **📊 可视化仪表盘**：利用 **Plotly** 绘制能力画像雷达图，直观展现优劣势。
* **🖥️ 极简 GUI 交互**：基于 `Streamlit` 构建，支持视频拖拽、报告一键导出。

---

## 🛠️ 技术栈

| 领域 | 技术实现 |
| :--- | :--- |
| **音频转录** | WhisperX (Tiny/Base/Small) |
| **大模型引擎** | 豆包 Doubao-Pro (OpenAI SDK 兼容) |
| **知识检索 (RAG)** | LangChain + Sentence-Transformers |
| **数据中心 (SaaS)** | Supabase (PostgreSQL) |
| **数据可视化** | Plotly + Pandas |
| **界面开发** | Streamlit + Custom CSS |

---

## 🚀 快速开始

### 1. 环境准备
确保系统中已安装 **FFmpeg**，然后克隆并安装依赖：

```bash
# 克隆仓库
git clone https://github.com/wyttao120/AI-Interview-Coach.git
cd AI-Interview-Coach

# 安装核心依赖
pip install -r requirements.txt
```


### 2. 配置 API 密钥
在项目根目录创建 .env 文件，填入你的云端凭证：

```Bash
# 火山引擎 (豆包 AI)
VOLC_API_KEY=你的 API 密钥
DOUBAO_ENDPOINT_ID=你的接入点 ID

# Supabase (云端数据库)
SUPABASE_URL=你的项目 URL
SUPABASE_KEY=你的匿名密钥 (Anon Key)
```

### 3. 运行程序
```Bash
# 启动网页版 (推荐：含可视化看板)
streamlit run app.py

# 启动命令行版 (快速调试)
python run_interview.py
```

---

## 📺 视觉预览 (Visual Showcase)
```bash
1. SaaS 化量化看板
集成指标卡片与能力雷达图，面试表现一目了然。

<p align="center">
<img src="assets/dashboard_metrics.png" width="900" alt="看板预览">
</p>
```

```bash
2. 长期成长趋势
自动调取 Supabase 历史数据，追踪 WPM 语速波动与得分进化。

<p align="center">
<img src="assets/growth_curve.png" width="900" alt="成长曲线">
</p>
```

## 🛡️ 安全与隐私
* **密钥安全**：项目通过 .gitignore 严格过滤 .env 文件，确保 API 凭据不泄露。

* **数据持久化**：采用 Supabase Row Level Security (RLS) 理念设计，确保面试数据的私密性。

## 🤝 贡献与支持
欢迎提交 Issue 或 Pull Request。如果你觉得这个工具有用，请给个 Star ⭐！

## 📄 开源协议
本项目采用 MIT License 许可。