"""
업그레이드 버전:
- /ws/{browser} : 화면 프레임을 실시간으로 계속 흘려보내는 웹소켓
- /run/{browser} : 버튼 눌렀을 때 실제 테스트 동작(검색)을 실행하는 API

실행:
    uvicorn app:app --reload

브라우저에서 확인:
    http://127.0.0.1:8000
"""

import sys
import asyncio

# 윈도우에서 uvicorn --reload 쓸 때 기본 이벤트루프가 SelectorEventLoop로 잡혀서
# Playwright가 브라우저를 서브프로세스로 못 켜는 문제(NotImplementedError)가 생김.
# ProactorEventLoop를 명시적으로 지정해서 해결.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

import browser_manager as bm

app = FastAPI()


@app.get("/")
def index():
    return FileResponse("index.html")


@app.websocket("/ws/{browser}")
async def websocket_endpoint(websocket: WebSocket, browser: str):
    await websocket.accept()
    session = await bm.get_session(browser)  # 없으면 이때 브라우저가 새로 켜짐
    session.websocket = websocket

    try:
        while True:
            # 딱히 프론트에서 보내는 메시지는 없지만, 연결 유지를 위해 대기
            await websocket.receive_text()
    except WebSocketDisconnect:
        session.websocket = None


@app.post("/run/{browser}")
async def run_browser_test(browser: str):
    if browser not in ("chrome", "edge"):
        return {"error": f"지원하지 않는 브라우저: {browser}"}

    session = await bm.get_session(browser)
    passed, value = await session.run_naver_test()

    return {"browser": browser, "pass": passed, "value": value}
