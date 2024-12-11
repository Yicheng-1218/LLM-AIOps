from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from random import random
import os
import re
from dotenv import load_dotenv
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
    ShowLoadingAnimationRequest
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from module.agent import proxmox_agent


load_dotenv()
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

DNS=None

app = FastAPI(
    title="AIOps API",
    description="Proxmox VE AIOps系統API",
    version="1.0.0"
)

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有方法
    allow_headers=["*"],  # 允許所有標頭
)

@app.get("/")
async def root():
    return {"message": "hello world"}

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    try:
        global DNS
        if DNS is None:
            # 從 HTTP 標頭中取得 DNS
            DNS = f'{request.headers['X-Forwarded-Proto']}://{request.headers['X-Forwarded-Host']}'
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return "OK"

@app.get("/screenshot")
async def get_screenshot():
    # 檢查圖片是否存在
    screenshot_path = './AIOps/screenshots/screenshot.png'
    if os.path.exists(screenshot_path):
        return FileResponse(screenshot_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="找不到截圖")


user_history = {}

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event:MessageEvent):
    with ApiClient(configuration) as api_client:
        try:
            line_bot_api = MessagingApi(api_client)
            user_message = event.message.text
            user_id = event.source.user_id
            
            # 檢查使用者是否有歷史紀錄,沒有則創建新的
            if user_id not in user_history:
                user_history[user_id] = event.reply_token
            
            # 如果使用者輸入 /forget，則清除歷史紀錄
            if user_message=='/forget':
                if user_id in user_history:
                    del user_history[user_id]
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text='記憶已清除')]
                    ))
                return
                
            # 顯示載入動畫
            line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(
                chatId=user_id,
                loadingSeconds=60
            ),async_req=True).get()
            
            # thread_id 是對話紀錄的唯一識別碼
            config = {
                "configurable": {
                    "thread_id": user_history.get(user_id),
                    "remaining_steps": 100
                }
            }
            
            try:
                messages = []
                # AI 模型串流回覆
                for s in proxmox_agent.stream({'messages': user_message}, config, stream_mode='values'):
                    # 取得最後一條訊息
                    stream_message = s['messages'][-1]
                    
                    # 如果調用截圖工具，則建立圖片訊息
                    if stream_message.name=='screenshot_proxmox_ve':
                        image_url = f'{DNS}/screenshot?rand={random()}'
                        image_message = ImageMessage(
                                type='image',
                                originalContentUrl=image_url,
                                previewImageUrl=image_url
                            )
                        messages.append(image_message)
                messages.insert(0,TextMessage(text=stream_message.content))
                
                # 檢查是否有確認訊息
                if isinstance(messages[-1],TextMessage):
                    patten = r'<confirm>(.*?)</confirm>'
                    if confirm := re.search(patten, messages[-1].text, re.DOTALL):
                        messages[-1].text = re.sub(patten,'請於下方進行確認~',messages[-1].text,flags=re.DOTALL)
                        messages.append(TextMessage(text='【確認訊息】:\n'+confirm.group(1).strip()))
                
                
                    
            except Exception as e:
                # 處理 Anthropic API 或其他錯誤
                error_message = f"處理訊息時發生錯誤: {str(e)}"
                messages=[TextMessage(text=error_message)]
                
            # 回覆訊息
            line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
            ))
        except Exception as e:
            print(f"LINE API 錯誤: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("app:app", port=8000, reload=True)
