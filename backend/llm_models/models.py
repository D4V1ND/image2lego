from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os

temperature = 0.5
max_tokens = 8192

model_ollama = ChatOllama(
    model = "qwen3-vl:8b", 
    temperature=0.5,
    max_new_tokens=8192
)

load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

model_azure = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
    api_version=AZURE_OPENAI_VERSION,
    api_key=AZURE_OPENAI_API_KEY
)