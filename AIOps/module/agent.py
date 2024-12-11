from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
import requests
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from typing import Optional, Dict, Any
import os
import json
import logging
import warnings
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from .scrapy.screenshot import get_pve_screenshot

load_dotenv(override=True)
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
memory = MemorySaver()

# 設置日誌配置
logging.basicConfig(
    filename='proxmox_api.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


class ToolRegistry:
    _tools={}
    
    @classmethod
    def register(cls,func):
        """裝飾器，用於註冊工具"""
        # 先使用 langchain 的 @tool 裝飾器
        decorated_func = tool(func)
        cls._tools[func.__name__] = decorated_func
        return decorated_func

    @classmethod
    def tools(cls):
        """取得所有註冊的工具"""
        return list(cls._tools.values())
    

class FaissRetriever:
    def __init__(self,model_name) -> None:
        print("載入模型中...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'}, # 如果有 GPU 可以改為 'cuda'
            encode_kwargs={'normalize_embeddings': True})
        print("模型載入完成")
    
    def load_index(self,index_path) -> FAISS:
        print("載入 Faiss index...")
        if not os.path.exists(index_path):
           raise FileNotFoundError(f"路徑不存在: {index_path}")
        vectorstore = FAISS.load_local(index_path, self.embeddings,allow_dangerous_deserialization=True)
        print("Faiss index 載入完成")
        return vectorstore


class ProxmoxAPI:
    HOST=os.getenv('PVE_HOST')
    PORT=os.getenv('PVE_PORT')
    base_url=f'https://{HOST}:{PORT}/api2/json'
    headers={
        'Authorization': f'PVEAPIToken={os.getenv('PVE_USER_ID')}={os.getenv('PVE_API_KEY')}'
    }

    @classmethod
    def execute_request(cls, method: str, endpoint: str, params: Optional[Dict] = None):
        """執行 REST 請求"""
        url = f"{cls.base_url}{endpoint}"
             
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=cls.headers,
                params=params,
                verify=False
            )
            
            # 檢查響應狀態，如果不是 2xx，則拋出異常
            response.raise_for_status()
            response_data = response.json()
            
            logger.info(f'API Request: {method} {url} "HTTP/1.1 {response.status_code} {response.reason}"')
            
            return response_data
            
        except Exception as e:
            # 記錄異常
            logger.error(f"API Exception: {str(e)}", exc_info=True)
            return {"error": str(e)}



@ToolRegistry.register
def excute_proxmox_api(api_schema:str):
    """
    執行 Proxmox API 請求。    
    api_schema 應該是一個 JSON 字串，包含以下欄位：
    {
        "method": "GET/POST/PUT/DELETE",
        "endpoint": "/nodes/{node}/status",
        "params": {} (可選)
    }
    """
    try:
        schema = json.loads(api_schema)
        # 驗證必要欄位
        if not all(k in schema for k in ["method", "endpoint"]):
            return {"error": "缺少必要欄位"}
        
        # 執行請求
        return ProxmoxAPI.execute_request(
            method=schema["method"],
            endpoint=schema["endpoint"],
            params=schema.get("params")
        )
    except json.JSONDecodeError:
        return {"error": "無效的 JSON 格式"}
    except Exception as e:
        return {"error": str(e)}


faiss = FaissRetriever(model_name='BAAI/bge-base-zh-v1.5')

# 載入 Faiss index
api_index = faiss.load_index(index_path='C:/Users/S00180/Desktop/Project/NL2Query/AIOps/faiss/api_index')
trouble_shooting_index = faiss.load_index(index_path='C:/Users/S00180/Desktop/Project/NL2Query/AIOps/faiss/trouble_shooting_index')

# 建立retriever，相似度前3
api_retriever = api_index.as_retriever(search_kwargs={"k": 3})
trouble_shooting_retriever = trouble_shooting_index.as_retriever(search_kwargs={"k": 3})

@ToolRegistry.register
def api_docs_retriever(query:str):
    """
    搜尋Proxmox VE API的使用文檔。文檔提供了有關Proxmox VE API的詳細信息，包括端點、參數和請求方法。
    """
    return api_retriever.invoke(query)

@ToolRegistry.register
def trouble_shooting_doc_retriever(query:str):
    """
    搜尋Proxmox VE故障排除指南。這些指南包含了Proxmox VE的常見問題和解決方案。
    必須使用繁體中文查詢。
    """
    return trouble_shooting_retriever.invoke(query)

@ToolRegistry.register
def screenshot_proxmox_ve():
    """
    截取 Proxmox VE 的介面截圖。
    """
    save_path = './AIOps/screenshots/screenshot.png'
    result = get_pve_screenshot(save_path)
    return {"message": "截圖已保存"} if result else {"error": "截圖失敗"}

'''
回答的時候可以加入一些幽默的元素，但不要過於調皮。
回答的時候可以加入一些專業術語，但不要過於冷漠。
回答的時候可以加入一些顏文字，但不要過於頻繁。
'''

system_prompt = """
你是AI維運助手，是精通 Proxmox VE 的專家。
你的名子叫做 Mia，是一個年輕女性。
你的回答語氣必須溫柔活潑且專業，你是一個女秘書把用戶當成主人一樣對待。
可以使用一些顏文字和幽默的元素，但不要過於調皮。

你的任務是：
- 理解用戶的需求 (若用戶沒有特別要求執行工具，就不要隨意使用工具)
- 根據需求查詢 Proxmox VE API 使用文檔或故障排除指南
- 將需求轉換為適當的 Proxmox API 請求
- 生成正確的 API schema JSON
- 使用 execute_proxmox_api 工具執行請求 
- 統整解析並說明結果

請一步一步思考並執行：
- 分析用戶需求
(若問題與 Proxmox VE操作無關，就不要隨意使用工具，直接回覆用戶並結束對話)
- 查詢 API 使用文檔或故障排除指南
- 選擇合適的 API endpoint
- 生成 API schema
- 執行請求
- 統整解釋結果

# 因為系統設定只有你的最後一則的訊息會呈現給用戶，請確保你最後一則訊息是你想要呈現給用戶的統整解釋。
# 前面思考的部分不會被用戶看到，所以不用過多描述。
# 若execute_proxmox_api操作涉及:新增、修改、刪除。請暫停後續所有動作，並覆述用戶的需求，請求用戶確認。
# 在對話中針對需要用戶確認的操作，請置於末尾詢問，並在前後加上<confirm>...</confirm>標籤。
# 用戶確認的訊息必須完全包含指定的文字，否則將被視為拒絕。如: AI: 請下達「確認xx」指示， Human: 確認xx
# 若execute_proxmox_api回傳是UPID開頭，請擷取一張圖片讓用戶查看，否則不要截圖。
"""


tools = ToolRegistry.tools()
proxmox_agent = create_react_agent(llm, tools, state_modifier=system_prompt, checkpointer=memory)
