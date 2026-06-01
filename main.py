import base64
import hashlib
import os

import requests
import streamlit as st

from ai_analyzer import analyze_with_ai
from schema import POLICY_ITEMS
from screen_shot import take_screenshot

os.system("playwright install chromium")

GEMINI_MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
PREFERRED_MODEL_IDS = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]
SPECIALIZED_MODEL_KEYWORDS = (
    "antigravity",
    "computer-use",
    "customtools",
    "deep-research",
    "gemma",
    "image",
    "lyria",
    "pro",
    "robotics",
    "tts",
)


def sanitize_model_error(message: str, api_key: str) -> str:
    """Avoid echoing user API keys back into the UI."""
    if api_key:
        message = message.replace(api_key, "[API key]")
    return message.strip()


def is_specialized_model(model_id: str) -> bool:
    """Return true for models that are poor defaults for text website analysis."""
    return any(keyword in model_id for keyword in SPECIALIZED_MODEL_KEYWORDS)


def model_sort_key(model: dict[str, str]) -> tuple[int, int, str]:
    """Prefer low-quota general text models while preserving all returned choices."""
    model_id = model["id"]
    if model_id in PREFERRED_MODEL_IDS:
        return (0, PREFERRED_MODEL_IDS.index(model_id), model_id)
    if is_specialized_model(model_id):
        return (2, 0, model_id)
    return (1, 0, model_id)


def build_model_label(model_id: str, display_name: str) -> str:
    """Build a user-facing model label with quota risk hints."""
    label = f"{display_name} ({model_id})"
    if is_specialized_model(model_id):
        label += " - specialized/quota-limited"
    return label


def fetch_available_models(api_key: str) -> tuple[list[dict[str, str]], str | None]:
    """Fetch Gemini models available to the provided API key."""
    models: list[dict[str, str]] = []
    page_token = None

    try:
        while True:
            params = {"key": api_key, "pageSize": 1000}
            if page_token:
                params["pageToken"] = page_token

            response = requests.get(
                GEMINI_MODELS_ENDPOINT,
                params=params,
                timeout=15,
            )
            if response.status_code != 200:
                try:
                    message = response.json().get("error", {}).get("message")
                except ValueError:
                    message = response.text
                error_detail = sanitize_model_error(
                    message or response.reason,
                    api_key,
                )
                return [], f"Failed to fetch models: {error_detail}"

            payload = response.json()
            for model in payload.get("models", []):
                if "generateContent" not in model.get(
                    "supportedGenerationMethods",
                    [],
                ):
                    continue

                name = model.get("name", "")
                model_id = name.removeprefix("models/")
                if not model_id:
                    continue

                display_name = model.get("displayName") or model_id
                models.append(
                    {
                        "id": model_id,
                        "label": build_model_label(model_id, display_name),
                    },
                )

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

    except requests.RequestException as e:
        return [], f"Failed to fetch models: {sanitize_model_error(str(e), api_key)}"

    models.sort(key=model_sort_key)
    return models, None


def get_available_models(api_key: str) -> tuple[list[dict[str, str]], str | None]:
    """Return cached model options for the current Streamlit session."""
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    cache = st.session_state.get("model_options_cache")

    if cache and cache.get("key_hash") == key_hash:
        return cache["models"], cache["error"]

    models, error = fetch_available_models(api_key)
    st.session_state.model_options_cache = {
        "key_hash": key_hash,
        "models": models,
        "error": error,
    }
    return models, error


def process_url(
    url: str,
    selected_policies: list[str],
    api_key: str,
    model_name: str,
) -> dict:
    """Process a single URL and return the result"""
    result = {
        "url": url,
        "violated_policy": "Processing...",
        "reason": "",
        "location_of_violation": "",
        "screenshot_base64": None,
        "xpath": None,
        "error": None,
    }

    try:
        # Analyze with AI (get XPath first)
        analysis = analyze_with_ai(
            url,
            selected_policies,
            api_key,
            model_name,
        )

        result["violated_policy"] = analysis.violated_policy
        result["reason"] = analysis.reason
        result["location_of_violation"] = getattr(
            analysis,
            "location_of_violation",
            "",
        )
        result["xpath"] = getattr(analysis, "xpath", None)

        # Take screenshot and encode as base64
        screenshot_base64 = take_screenshot(url, result["xpath"])
        if screenshot_base64:
            result["screenshot_base64"] = screenshot_base64
        else:
            result["error"] = "Failed to take screenshot"

    except Exception as e:
        result["error"] = str(e)
        result["violated_policy"] = "Error"
        result["reason"] = f"Processing error: {e!s}"

    return result


def main():
    st.set_page_config(
        page_title="Website Auto Policy Violation Checker",
        page_icon="📚",
        layout="wide",
    )

    st.title("📚 Website Auto Policy Violation Checker")

    # GitHub link
    st.markdown(
        """
        <div style="text-align: right; margin-bottom: 10px;">
            <a href="https://github.com/poopootra/ai-policy-checker" target="_blank" style="text-decoration: none; color: inherit;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="vertical-align: middle;">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                <span style="margin-left: 5px; vertical-align: middle;">View on GitHub</span>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("""
    AI-powered content policy violation checker\n
    This app is a tool that helps you check if a website violates any of the policies.
    You can enter multiple URLs separated by new lines and select the policies to check.
    The app will analyze the website and return the results.
    You wil need to enter your API key for the selected AI model.
    You can check get your API key from the following URL:
    [Google AI Studio](https://aistudio.google.com/app/api-keys)\n
    Some Gemini models may require a valid billing account.
    """)

    # Initialize session state
    if "results" not in st.session_state:
        st.session_state.results = []

    # Initialize analyzing state
    if "is_analyzing" not in st.session_state:
        st.session_state.is_analyzing = False

    # Settings section
    with st.sidebar:
        st.header("⚙️ Settings")

        api_key = st.text_input(
            "API Key",
            type="password",
            help="Enter your API key for the selected AI model",
            disabled=st.session_state.is_analyzing,
        )
        api_key = api_key.strip()

        model_options = []
        model_error = None
        if api_key:
            with st.spinner("Loading models..."):
                model_options, model_error = get_available_models(api_key)

        if api_key and model_options:
            model_ids = [model["id"] for model in model_options]
            model_labels = {model["id"]: model["label"] for model in model_options}
            model_name = st.selectbox(
                "AI Model",
                options=model_ids,
                index=0,
                format_func=lambda model_id: model_labels.get(model_id, model_id),
                help="Select the AI model to use (langchain literal format)",
                disabled=st.session_state.is_analyzing,
            )
        else:
            placeholder = (
                "Enter an API key first"
                if not api_key
                else "No compatible models available"
            )
            st.selectbox(
                "AI Model",
                options=[placeholder],
                index=0,
                disabled=True,
            )
            model_name = None

        if model_error:
            st.error(model_error)
        elif api_key and not model_options:
            st.warning("No generateContent-compatible models were returned.")

        st.divider()

        st.header("📋 Policy Selection")
        st.markdown("Select policies to check:")

        selected_policies = []
        # Set checkboxes to be selected by default
        for policy in POLICY_ITEMS:
            if st.checkbox(
                policy,
                key=f"policy_{policy}",
                value=True,
                disabled=st.session_state.is_analyzing,
            ):
                selected_policies.append(policy)

    # Main content
    st.header("🔗 URL Input")

    url_input = st.text_area(
        "Enter URLs (one per line). You can enter the same URL multiple times.",
        height=150,
        help="Enter multiple URLs, one per line",
        disabled=st.session_state.is_analyzing,
    )

    analyze_btn = st.button(
        "🔄 Analyzing..." if st.session_state.is_analyzing else "🚀 Analyze URLs",
        type="primary",
        disabled=st.session_state.is_analyzing,
    )
    if analyze_btn:
        # Validation check
        if not api_key:
            st.error("Please enter an API key")
            return

        if not model_name:
            st.error("Please select an AI model")
            return

        if not selected_policies:
            st.error("Please select at least one policy to check")
            return

        if not url_input.strip():
            st.error("Please enter at least one URL")
            return

        urls = [url.strip() for url in url_input.split("\n") if url.strip()]

        if not urls:
            st.error("No valid URLs found")
            return

        # Set processing state after validation passes
        st.session_state.is_analyzing = True
        # Save values to session state (for use after rerun)
        st.session_state.url_input = url_input
        st.session_state.api_key = api_key
        st.session_state.selected_policies = selected_policies
        st.session_state.model_name = model_name
        st.session_state.urls = urls
        # Rerun to update UI
        st.rerun()

    # Execute actual processing if analyzing
    if st.session_state.is_analyzing and "urls" in st.session_state:
        try:
            urls = st.session_state.urls
            api_key = st.session_state.api_key
            selected_policies = st.session_state.selected_policies
            model_name = st.session_state.model_name

            st.session_state.results = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, url in enumerate(urls):
                status_text.text(f"Processing {i + 1}/{len(urls)}: {url}")
                progress_bar.progress((i + 1) / len(urls))

                result = process_url(
                    url,
                    selected_policies,
                    api_key,
                    model_name,
                )
                st.session_state.results.append(result)

            status_text.text("✅ Analysis complete!")
            progress_bar.empty()

            # Clear session state after processing completes
            if "urls" in st.session_state:
                del st.session_state.urls

        except Exception as e:
            st.error(f"An error occurred during processing: {e!s}")
        finally:
            # Set is_analyzing to False after all processing completes
            st.session_state.is_analyzing = False
            # Update UI to enable button
            st.rerun()

    # Results display section
    if st.session_state.results:
        st.header("📊 Results")

        # Results table
        results_data = []
        for result in st.session_state.results:
            results_data.append(
                {
                    "URL": result["url"],
                    "Violated Policy": result["violated_policy"],
                    "Reason": result["reason"],
                    "Location of Violation": result.get(
                        "location_of_violation",
                        "",
                    ),
                },
            )

        st.dataframe(results_data, width="stretch")

        # Detailed display
        st.header("📸 Detailed Results")

        for i, result in enumerate(st.session_state.results):
            with st.expander(f"🔍 {result['url']}", expanded=False):
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.subheader("Analysis Result")
                    st.write(f"**Violated Policy:** {result['violated_policy']}")
                    st.write("**Reason:**")
                    st.write(result["reason"])

                    if result.get("error"):
                        st.error(f"Error: {result['error']}")

                with col2:
                    if result.get("location_of_violation"):
                        st.write("**Location of Violation:**")
                        st.write(result["location_of_violation"])

                    st.subheader("Screenshot")
                    if result.get("screenshot_base64"):
                        try:
                            # Display image from base64 string
                            screenshot_data = base64.b64decode(
                                result["screenshot_base64"],
                            )
                            st.image(
                                screenshot_data,
                                caption=result["url"],
                                width="stretch",
                            )
                        except Exception as e:
                            st.error(f"Failed to load screenshot: {e!s}")
                    else:
                        st.warning("Screenshot not available")


if __name__ == "__main__":
    main()
