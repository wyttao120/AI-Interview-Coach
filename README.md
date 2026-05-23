# AI 面试分析与训练系统

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-black.svg)](https://nextjs.org/)
[![Database](https://img.shields.io/badge/Database-Supabase-blueviolet.svg)](https://supabase.com/)

> 面向求职场景的 AI 面试分析与训练系统。基于语音转录、结构化 Prompt 与多阶段分析机制，实现面试内容解析、技术诊断、追问训练与成长轨迹建模。

> 当前 GitHub 仓库仅保留早期验证大模型编排链路的核心 MVP 代码供技术交流。 最新线上版本已演进为 Next.js + FastAPI 前后端分离架构。
> 体验地址：[ai-fupan.cn](https://www.ai-fupan.cn)

---

## 目录

- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 端点一览](#api-端点一览)
- [配置说明](#配置说明)

---

## 核心功能

### 多阶段 AI 分析流程

针对长文本面试转录场景，设计多阶段 AI 分析流程，对转录内容进行证据提取、技能归因与关键问题归因分析，并通过阶段拆分与结构化摘要降低长上下文分析中的信息干扰问题。

分析流程包含：

| 阶段 | 说明 |
|------|------|
| 文件上传 | 支持 MP3/WAV/M4A/FLAC 等音频格式，进行 MIME 魔数校验 |
| ASR 转写 | 基于 DashScope Paraformer-v2 进行语音识别与说话人分离 |
| 量化指标 | 统计语速 WPM、填充词密度、长停顿与沉默比等表达特征 |
| LLM 分析 | 基于结构化 Prompt 与双消息架构生成分析结果 |
| 深度诊断 | 执行证据提取、转录分段、能力画像与质量评估 |
| 成长轨迹 | 对历史面试数据进行趋势分析与阶段性对比 |

关键实现：
- 将长文本分析拆分为多个阶段，减少单次 Prompt 的上下文压力
- 对中间结果进行结构化摘要，避免后续阶段的信息污染
- 使用独立分析阶段处理能力画像与问题归因，降低分析结果耦合

### 语音表达能力分析

基于 ASR 与说话人分离实现面试音频结构化处理，并结合语速、停顿与填充词等时序特征构建表达能力指标体系，用于定位连续追问场景下的表达波动区间。

关键指标包括：
- WPM（Words Per Minute）语速统计
- 填充词频率与分钟级分布
- 长停顿检测
- 沉默时间占比

关键实现：
- 基于 ASR 分段结果统计时序特征
- 对连续追问场景进行表达波动检测
- 支持历史面试数据的指标趋势对比

### Prompt 分层提示系统

构建包含角色策略、Few-shot 示例与运行时上下文拼装的 Prompt 生成机制，提升复杂分析场景下输出结果的一致性与结构化程度。

Prompt 主要包含：
- 角色策略层
- Few-shot 示例层
- 运行时上下文层
- 输出格式约束层

关键实现：
- 使用 YAML 配置管理 Prompt 模板
- 动态拼装分析上下文与历史摘要
- 通过输出约束降低复杂分析任务中的结果波动

### AI 追问训练系统

基于诊断结果动态生成追问问题，并结合阶段化训练流程，实现连续追问场景下的模拟训练与实时反馈。

训练流程包含：
- warmup：基础问题热身
- pressure：连续追问压力测试
- stabilization：表达恢复与稳定阶段

关键实现：
- 根据诊断结果动态生成追问方向
- 基于训练阶段调整问题强度
- 结合语速与填充词等指标生成实时反馈

### 上下文感知对话系统

融合历史面试数据、结构化分析结果与当前会话状态，实现复盘问答与跨轮次对比分析，并通过上下文精简降低长对话场景下的上下文冗余问题。

关键实现：
- 自动注入历史面试摘要与分析结果
- 对长对话历史进行摘要压缩
- 基于当前会话阶段动态裁剪上下文内容

### 面试数据存储与成长分析

构建面试数据持久化与历史表现对比机制，对语速、停顿与填充词等指标进行多次面试趋势分析，用于观察候选人的阶段性表达变化。

关键实现：
- 存储结构化面试分析结果
- 支持历史面试数据聚合与趋势统计
- 对表达能力指标进行阶段性变化分析

---

## 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| FastAPI (Python 3.10+) | Web 框架 |
| Supabase (PostgreSQL) | 数据库与认证 |
| Redis | 缓存与限流 |
| DeepSeek API | LLM 推理 |
| DashScope | ASR 语音转文字 / OCR |

### 前端

| 技术 | 用途 |
|------|------|
| Next.js 16 (App Router) | 前端框架 |
| TypeScript | 语言 |
| Tailwind CSS | 样式 |

---

---

## 快速开始

### 环境准备

需要 Python 3.10+、Node.js 18+ 以及 FFmpeg。

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# Supabase
SUPABASE_URL=你的项目URL
SUPABASE_KEY=你的anon key
SUPABASE_SERVICE_ROLE_KEY=你的service_role key

# DeepSeek
DEEPSEEK_API_KEY=你的API密钥
DEEPSEEK_MODEL=deepseek-v4-flash

# DashScope（语音转文字）
DASHSCOPE_API_KEY=你的API密钥

# 邮箱（验证码发送）
EMAIL_SENDER=your_email@163.com
EMAIL_AUTH_CODE=你的邮箱授权码
```

### 启动服务

```bash
# 后端
cd backend
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

访问 http://localhost:3000 即可使用。

---

## API 端点一览

| 模块 | 前缀 | 主要功能 |
|------|------|---------|
| auth | `/auth` | 注册/登录/验证码/密码重置 |
| interview | `/interviews` | 面试记录查询 |
| billing | `/billing` | 余额/兑换/流水 |
| upload | `/upload` | 文件上传/文字提取 |
| ai | `/ai` | AI 对话 |
| chat | `/chat` | 聊天线程/消息管理 |
| admin | `/admin` | 管理后台 |
| creator | `/creator` | 创作者中心 |
| invite | `/invite` | 邀请码与绑定 |
| analyze | `/analyze` | 分析任务提交/进度/取消 |
| training | `/training` | 追问训练 |

---

## 配置说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| SUPABASE_URL | — | Supabase 项目 URL |
| SUPABASE_KEY | — | anon public key |
| SUPABASE_SERVICE_ROLE_KEY | — | service_role 密钥 |
| DEEPSEEK_API_KEY | — | DeepSeek API Key |
| DEEPSEEK_MODEL | deepseek-v4-flash | LLM 模型 |
| DASHSCOPE_API_KEY | — | DashScope API Key |
| EMAIL_SENDER | — | 发件邮箱 |
| EMAIL_AUTH_CODE | — | 邮箱授权码 |
| REDIS_URL | redis://localhost:6379/0 | Redis 连接地址 |
