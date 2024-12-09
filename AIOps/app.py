from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from random import random
import os
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

app = FastAPI(
    title="AIOps API",
    description="AIOps 系統 API",
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
    return {"message": "歡迎使用 AIOps API"}

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

@app.get("/screenshot")
async def get_screenshot():
    # 檢查圖片是否存在
    screenshot_path = './AIOps/screenshot/screenshot.png'
    if os.path.exists(screenshot_path):
        return FileResponse(screenshot_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="找不到截圖")


history_id = None
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event:MessageEvent):
    with ApiClient(configuration) as api_client:
        try:
            line_bot_api = MessagingApi(api_client)
            user_message = event.message.text
            global history_id
            if history_id is None:
                history_id = event.reply_token
            if user_message=='/forget':
                history_id = None
                line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text='記憶已清除')]
                ))
                return
                
                
            thread = line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(
                chatId=event.source.user_id,
                loadingSeconds=60
            ),async_req=True)
            thread.get()
            
            
            config = {
                "configurable": {
                    "thread_id": history_id,
                    "remaining_steps": 100
                }
            }
            try:
                messages = []
                for s in proxmox_agent.stream({'messages': user_message}, config, stream_mode='values'):
                    stream_message = s['messages'][-1]
                    if stream_message.name=='screenshot_proxmox_ve':
                        image_url = f'https://a40f-202-39-170-58.ngrok-free.app/screenshot?rand={random()}'
                        image_message = ImageMessage(
                                type='image',
                                originalContentUrl=image_url,
                                previewImageUrl=image_url
                            )
                        messages.append(image_message)
                messages.insert(0,TextMessage(text=stream_message.content))
                
                    
            except Exception as e:
                # 處理 Anthropic API 或其他錯誤
                error_message = f"處理訊息時發生錯誤: {str(e)}"
                messages=[TextMessage(text=error_message)]
                
            
            line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
            ))
        except Exception as e:
            print(f"LINE API 錯誤: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("app:app", port=8000, reload=True)
