import os
from langchain.text_splitter import RecursiveCharacterTextSplitter

from smolagents import Tool, CodeAgent, LiteLLMModel

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


pdf_directory = "pdfs"
pdf_files = [
    os.path.join(pdf_directory, f)
    for f in os.listdir(pdf_directory)
    if f.endswith(".pdf")
]
docs = []

for file_path in pdf_files:
    loader = PyPDFLoader(file_path)
    docs.extend(loader.load())

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    add_start_index=True,
    strip_whitespace=True,
    separators=["\n\n", "\n", ".", " ", ""],
)

docs_processed = text_splitter.split_documents(docs)

# Initialize embeddings and ChromaDB vector store

# from langchain_huggingface import HuggingFaceEmbeddings
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = Chroma.from_documents(
    docs_processed, embeddings, persist_directory="./chroma_db"
)


class RetrieverTool(Tool):
    name = "retriever"
    description = "Uses semantic search to retrieve the parts of documentation that could be most relevant to answer your query."
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to perform. This should be semantically close to your target documents. Use the affirmative form rather than a question.",
        }
    }
    output_type = "string"

    def __init__(self, vector_store, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = vector_store

    def forward(self, query: str) -> str:
        assert isinstance(query, str), "Your search query must be a string"
        docs = self.vector_store.similarity_search(query, k=3)
        return "\nRetrieved documents:\n" + "".join(
            [
                f"\n\n===== Document {str(i)} =====\n" + doc.page_content
                for i, doc in enumerate(docs)
            ]
        )


retriever_tool = RetrieverTool(vector_store)

# Choose which LLM engine to use!

# from smolagents import HfApiModel
# model = HfApiModel(model_id="meta-llama/Llama-3.3-70B-Instruct")

# from smolagents import TransformersModel
# model = TransformersModel(model_id="meta-llama/Llama-3.2-2B-Instruct")

# For anthropic: change model_id below to 'anthropic/claude-3-5-sonnet-20240620' and also change 'os.environ.get("ANTHROPIC_API_KEY")'
model = LiteLLMModel(
    model_id="groq/llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY"),
)
agent = CodeAgent(
    tools=[retriever_tool],
    model=model,
    max_steps=4,
    verbosity_level=2,
)

agent_output = agent.run("what is Position-wise Feed-Forward Networks")


print("Final output:")
print(agent_output)
