"""AI analyzer module using LangChain with structured output."""

from typing import Literal, get_type_hints

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, create_model

from policy_mapping import get_policy_markdown
from schema import POLICY_ITEMS


def create_policy_violation_analysis_model(
    policy_literals: list[str] = POLICY_ITEMS,
) -> type[BaseModel]:
    """Create a Pydantic model for policy violation analysis.

    This function generates a new Pydantic model that includes three fields:
    - `violated_policy`: A field that must be one of the values in `policy_literals`.
    - `reason`: A field that must be a string.
    """
    return create_model(
        "PolicyViolationAnalysis",
        violated_policy=(
            Literal[tuple(policy_literals)],
            Field(
                description=(
                    """
                The name of the violated policy from the selected policies list,
                you must find out the policy that is violated from the website content
                """
                ),
            ),
        ),
        reason=(
            str,
            Field(
                description=(
                    "Brief explanation of why this policy violation was identified, "
                    "referencing specific content from the website. "
                    "If no violation is found, provide a brief reason."
                    "You need to provide where they violated the policy in one sentence,"
                    "and description of it in another sentence, so 2 lines in total."
                ),
                example="The website is saying that they are selling CBD oils, but they are not licensed to sell CBD oils made from cannabis. This is against the policy of Legal requirements, because cannabis is a controlled substance in Japan, and thera are possibilities their cusomer abuse the product.",
            ),
        ),
        location_of_violation=(
            str,
            Field(
                description=(
                    "日本語で違反のある具体的な場所を簡潔に返してください。"
                    "ユーザーが簡単な説明で"
                ),
                examples=[
                    "トップページ画面中央の女性が商品を持った画像が示されているバナー広告",
                    "ページをスクロールして真ん中ほどの、緑の背景に「CBDオイル」という文字の記載がある部分",
                ],
            ),
        ),
        xpath=(
            str,
            Field(
                description=(
                    "A representative XPATH for the area or block most relevant to the policy violation, "
                    "rather than a single, narrowly-focused element. "
                    "Provide an XPATH that covers a broader section of the violation, such as a container or content block, "
                    "to help the user visually locate the problematic area within the page. "
                    "The location should be easily identifiable and give users sufficient context for manual review "
                    "and screenshot capture. Avoid pointing to a single word or minor span—use a container or major identifiable section."
                    "Instead of returning a element of text, return a container or major identifiable section that contains the violation."
                    "For example, if the violation is a text, return div contains the text and its description."
                    "If an image is violated, return the container of the image. Do not return xpath to locate text only like /*[contains(text(), 'example text')]"
                    "Beware not to return too wide range xpath that includes too many elements."
                ),
                example="xpath=/html/body/div[1]/div[1]/div[1]",
            ),
        ),
    )


RESPONSE_FORMAT = get_type_hints(create_policy_violation_analysis_model)["return"]


def analyze_with_ai(
    url: str,
    selected_policies: list[Literal[tuple(POLICY_ITEMS)]],
    api_key: str,
    model_name: str,
) -> RESPONSE_FORMAT:
    """Analyze the website with AI and return the policy violation analysis."""
    try:
        response_format = create_policy_violation_analysis_model(selected_policies)
        policy_markdown = get_policy_markdown(selected_policies)
        policy_prompt = "<policies_description>"
        for policy, markdown in policy_markdown.items():
            policy_prompt += f"""
            <policy_name>{policy}</policy_name>
            <policy_description>{markdown}</policy_description>
            """
        policy_prompt += "</policies_description>"

        system_prompt = f"""
        You are an expert content policy analyzer. Analyze the provided website content
        passed by url from user to determine if it violates any of the policies.
        Consider both the text content and any visual elements that might be visible
        passed by url from user.
        Be thorough in your analysis and provide specific reasons for your findings.
        Provide your answer based only on the contents of the website from the url.

        Always return output in the following format:
        <response_format>
        {response_format.model_json_schema()}
        </response_format>

        {policy_prompt}
        """

        user_prompt = f"""
        Analyze the following website:
        URL: {url}
        Please analyze this website and find out where it violates any of the policies.
        Recommended approach:
        1. Think carefully what the website is about and go through the page content.
        2. Find out the policy that is violated from the website content.
        3. Return 'violated_policy' and 'reason' fields in the json object format.
        """
        tools = []
        if model_name.startswith("openai:"):
            tools.append({"type": "web_search_preview"})
        if model_name.startswith("gemini"):
            tools.append({"url_context": {}})

        llm = ChatGoogleGenerativeAI(
            model=model_name,
            api_key=api_key,
            response_schema=response_format.model_json_schema(),
            response_mime_type="application/json",
            thinking_budget=1024,
        )
        llm_with_tools = llm.bind_tools(tools)

        result = llm_with_tools.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
        )
        output_text = result.content[-1].get("text", "")

        try:
            return response_format.model_validate_json(output_text)
        except Exception as e:
            raise Exception(f"Error parsing response: {e!s}")
    except Exception as e:
        raise Exception(f"AI analysis error: {e!s}")
