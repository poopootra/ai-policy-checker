"""Mapping of policy names to Google Ads policy URLs"""

import requests
from html_to_markdown import convert_to_markdown

mapping_dict = {
    "Counterfeit goods": "https://support.google.com/adspolicy/answer/176017?sjid=16476839465041943591-NC",
    "Dangerous products or services": "https://support.google.com/adspolicy/answer/6014299?sjid=16476839465041943591-NC",
    "Enabling dishonest behavior": "https://support.google.com/adspolicy/answer/6016086?sjid=16476839465041943591-NC",
    "Inappropriate content": "https://support.google.com/adspolicy/answer/6015406?sjid=16476839465041943591-NC",
    "Abusing the ad network": "https://support.google.com/adspolicy/answer/6020954?sjid=16476839465041943591-NC",
    "Data collection and use": "https://support.google.com/adspolicy/answer/6020956?sjid=16476839465041943591-NC",
    "Misrepresentation": "https://support.google.com/adspolicy/answer/6020955?sjid=16476839465041943591-NC",
    "Ad protections for children and teens": "https://support.google.com/adspolicy/answer/6023699?sjid=16476839465041943591-NC",
    "Alcohol": "https://support.google.com/adspolicy/answer/6012382?sjid=16476839465041943591-NC",
    "Gambling and games": "https://support.google.com/adspolicy/answer/6018017?sjid=16476839465041943591-NC",
    "Healthcare and medicines": "https://support.google.com/adspolicy/answer/176031?sjid=16476839465041943591-NC",
    "Political content": "https://support.google.com/adspolicy/answer/6014595?sjid=16476839465041943591-NC",
    "Financial products and services": "https://support.google.com/adspolicy/answer/2464998?sjid=16476839465041943591-NC",
    "Sexual content": "https://support.google.com/adspolicy/answer/6023699?sjid=4441517453548231022-NC",
    "Legal requirements": "https://support.google.com/adspolicy/answer/6023676?sjid=4441517453548231022-NC",
}


def extract_necessary_text(text: str) -> str:
    """Extract the necessary text from the policy markdown"""
    text = text.split("#### On this page\n\n", 1)[1]
    text = text.split("\n\n---\n\n\n", 1)[1]
    return text.split("Need help?")[0]


def get_policy_markdown(policies: list[str]) -> dict[str, str]:
    """Get the markdown of the policies"""
    output: dict[str, str] = {}
    try:
        for policy in policies:
            url = mapping_dict[policy]
            html = requests.get(url, timeout=10).text
            markdown = convert_to_markdown(html)
            output[policy] = extract_necessary_text(markdown)
    except Exception as e:
        raise Exception(f"Error getting policy markdown: {e!s}")
    finally:
        return output
