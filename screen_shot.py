"""Take a screenshot of the website using Playwright's async API and return as base64 string."""

import asyncio
import base64
import sys
import warnings

from playwright.async_api import async_playwright


async def take_xpath_screenshot(
    url: str,
    xpath: str | None = None,
) -> bytes | None:
    """Take a screenshot of a URL using Playwright's async API

    Args:
        url: URL to take screenshot of
        xpath: XPath of a specific element (if specified, only that element is screenshot)

    Returns:
        Byte data on success, None on failure

    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            screenshot_bytes = None
            if xpath:
                try:
                    # Get element by XPath
                    element = page.locator(f"xpath={xpath}").first
                    count = await element.count()
                    if count > 0:
                        # Take screenshot of the element if it exists
                        screenshot_bytes = await element.screenshot()
                    else:
                        # Take full page screenshot if element not found
                        screenshot_bytes = await page.screenshot(full_page=True)
                except Exception as e:
                    # Take full page screenshot if XPath is invalid
                    warnings.warn(
                        f"XPath '{xpath}' is invalid or element not found. Taking full page screenshot: {e!s}",
                        stacklevel=2,
                    )
                    screenshot_bytes = await page.screenshot(full_page=True)
            else:
                # Take full page screenshot if XPath is not specified
                screenshot_bytes = await page.screenshot(full_page=True)

            await browser.close()
            return screenshot_bytes
    except Exception as e:
        warnings.warn(f"Screenshot error for {url}: {e!s}", stacklevel=2)
        return None


def take_screenshot(url: str, xpath: str | None = None) -> str | None:
    """Take a screenshot of a URL using Playwright and return as base64 encoded string (synchronous wrapper)

    Args:
        url: URL to take screenshot of
        xpath: XPath of a specific element (if specified, only that element is screenshot)

    Returns:
        Base64 encoded string on success, None on failure

    """
    # Event loop policy settings for Windows environment
    if sys.platform == "win32":
        old_policy = None
        try:
            old_policy = asyncio.get_event_loop_policy()
            policy = asyncio.WindowsProactorEventLoopPolicy()
            asyncio.set_event_loop_policy(policy)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                screenshot_bytes = loop.run_until_complete(
                    take_xpath_screenshot(url, xpath),
                )
                if screenshot_bytes:
                    return base64.b64encode(screenshot_bytes).decode("utf-8")
                return None
            finally:
                loop.close()
        finally:
            if old_policy is not None:
                asyncio.set_event_loop_policy(old_policy)
    else:
        screenshot_bytes = asyncio.run(take_xpath_screenshot(url, xpath))
        if screenshot_bytes:
            return base64.b64encode(screenshot_bytes).decode("utf-8")
        return None
