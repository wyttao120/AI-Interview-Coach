import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 使用本地免费模型进行向量化（无需额外 API Key）
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def process_jd_to_context(file_path):
    """
    读取 JD 文件，提取最核心的 3 条岗位要求作为背景
    """
    try:
        # 1. 根据文件类型加载
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding='utf-8')
        
        documents = loader.load()

        # 2. 文本切片（JD 通常不长，切成 500 字一块）
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(documents)

        # 3. 创建临时向量数据库 (存放在内存中)
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vectorstore = Chroma.from_documents(docs, embeddings)

        # 4. 检索最相关的 3 个片段
        # 我们检索“岗位职责和任职要求”相关的核心内容
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        relevant_docs = retriever.invoke("岗位职责、任职要求、技术栈、核心能力")
        
        # 5. 合并成一段背景文字
        context = "\n".join([doc.page_content for doc in relevant_docs])
        return context

    except Exception as e:
        return f"解析 JD 失败: {str(e)}"
    finally:
        # 清理 Chroma 占用的资源（可选）
        pass