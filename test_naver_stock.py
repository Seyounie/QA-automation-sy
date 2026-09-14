"""
네이버 주식 종목 검색 테스트
플로우: 네이버 접속 -> "삼성전자 주가" 검색 -> 주가 숫자 노출되면 PASS

사용법:
    python test_naver_stock.py
"""

import re
from playwright.sync_api import sync_playwright

# "1,234,000" 같은 콤마 포함 숫자 패턴 = 주가로 간주
PRICE_PATTERN = re.compile(r"\d{1,3}(,\d{3})+")


def run_test(browser_name: str, channel: str | None = None):
    """
    browser_name: "chromium" (channel 지정 안 하면 기본 크롬 엔진)
    channel: "msedge" 로 주면 실제 설치된 엣지로 실행됨
    """
    label = channel if channel else browser_name

    with sync_playwright() as p:
        launch_args = {"headless": False}
        if channel:
            launch_args["channel"] = channel

        browser = getattr(p, browser_name).launch(**launch_args)
        page = browser.new_page()

        try:
            page.goto("https://www.naver.com")

            # 네이버 메인 검색창 id = "query" (2026.09 기준, 바뀌었으면 F12로 재확인)
            page.fill("#query", "삼성전자 주가")
            page.press("#query", "Enter")

            # 검색 결과 로딩 대기
            page.wait_for_load_state("networkidle")

            # 화면 전체 텍스트에서 주가 형태(콤마 숫자)가 있는지 확인
            body_text = page.inner_text("body")
            match = PRICE_PATTERN.search(body_text)

            if match:
                print(f"[{label}] PASS - 주가 노출 확인됨: {match.group()}")
                result = True
            else:
                print(f"[{label}] FAIL - 주가 패턴을 찾지 못함")
                result = False

        except Exception as e:
            print(f"[{label}] ERROR - {e}")
            result = False

        finally:
            page.wait_for_timeout(2000)  # 결과 눈으로 확인할 시간
            browser.close()

        return result


if __name__ == "__main__":
    print("=== 삼성전자 주가 검색 테스트 시작 ===")
    chrome_result = run_test("chromium")
    edge_result = run_test("chromium", channel="msedge")

    print("\n=== 결과 요약 ===")
    print(f"Chrome: {'PASS' if chrome_result else 'FAIL'}")
    print(f"Edge:   {'PASS' if edge_result else 'FAIL'}")
