"""
브라우저 세션을 계속 켜놓고(persistent),
CDP(Page.startScreencast)로 화면 프레임을 캡처해서
연결된 websocket으로 계속 전송하는 매니저.

핵심 개념:
- 브라우저를 매번 새로 켰다 끄지 않고, 한 번 켠 걸 계속 재사용함
- 그래야 "화면이 실시간으로 이어져서" 보임
- run_naver_test()는 이미 켜져있는 그 브라우저 위에서 그냥 동작만 수행함
"""

import asyncio
import re
from playwright.async_api import async_playwright

PRICE_PATTERN = re.compile(r"\d{1,3}(,\d{3})+")


class BrowserSession:
    def __init__(self, name: str, channel: str | None = None):
        self.name = name
        self.channel = channel
        self.playwright = None
        self.browser = None
        self.page = None
        self.cdp = None
        self.websocket = None  # 지금 연결된 프론트엔드 소켓 (없으면 None)

    async def start(self):
        self.playwright = await async_playwright().start()
        launch_args = {"headless": False}
        if self.channel:
            launch_args["channel"] = self.channel

        self.browser = await self.playwright.chromium.launch(**launch_args)
        self.page = await self.browser.new_page()
        await self.page.goto("https://www.naver.com")

        # CDP 세션 열고 스크린캐스트 시작
        self.cdp = await self.page.context.new_cdp_session(self.page)
        self.cdp.on("Page.screencastFrame", self._on_frame)
        await self.cdp.send(
            "Page.startScreencast",
            {"format": "jpeg", "quality": 60, "maxWidth": 800, "maxHeight": 600},
        )

    def _on_frame(self, params):
        # CDP 이벤트 콜백은 동기 함수라서, 비동기 전송은 task로 감싸서 실행
        asyncio.create_task(self._handle_frame(params))

    async def _handle_frame(self, params):
        if self.websocket is not None:
            try:
                await self.websocket.send_text(params["data"])
            except Exception:
                pass  # 소켓 끊긴 경우 등은 무시
        # 프레임 받았다고 CDP에 확인(ack) 안 해주면 다음 프레임이 안 옴
        await self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

    async def run_naver_test(self):
        await self.page.goto("https://www.naver.com")
        await self.page.fill("#query", "삼성전자 주가")
        await self.page.press("#query", "Enter")
        await self.page.wait_for_load_state("networkidle")

        body_text = await self.page.inner_text("body")
        match = PRICE_PATTERN.search(body_text)
        return bool(match), (match.group() if match else None)


# 브라우저 이름 -> 세션 객체 저장 (서버 켜있는 동안 계속 유지됨)
_sessions: dict[str, BrowserSession] = {}


async def get_session(name: str) -> BrowserSession:
    if name not in _sessions:
        channel = "msedge" if name == "edge" else None
        session = BrowserSession(name, channel=channel)
        await session.start()
        _sessions[name] = session
    return _sessions[name]
