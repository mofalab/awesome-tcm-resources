import os
import json
import logging
from typing import List

import requests
from pytrends.request import TrendReq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KEYWORDS = [
    "Chinese Medicine",
    "herbal product",
    "Taiwanese herbal formula",
]

TIMEFRAME = "now 7-d"  # last 7 days

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def fetch_trends(keywords: List[str]):
    pytrends = TrendReq(hl="en-US", tz=360)
    results = []
    for kw in keywords:
        try:
            pytrends.build_payload([kw], timeframe=TIMEFRAME)
            interest = pytrends.interest_over_time()
            if interest.empty:
                dynamic = 0
            else:
                dynamic = interest[kw].iloc[-1] - interest[kw].iloc[0]
            related = pytrends.related_queries()
            rising = []
            if kw in related and related[kw].get("rising") is not None:
                rising_df = related[kw]["rising"]
                rising = [row["query"] for _, row in rising_df.head(5).iterrows()]
            results.append({
                "keyword": kw,
                "dynamic": dynamic,
                "rising_queries": rising,
            })
        except Exception as e:
            logger.exception("Failed to fetch trend for %s", kw)
    return results


def format_message(trends: List[dict]) -> str:
    lines = ["*Google Trends Report*"]
    for t in trends:
        line = f"*{t['keyword']}*\nDynamic: {t['dynamic']}"
        if t['rising_queries']:
            line += "\nRising queries: " + ", ".join(t['rising_queries'])
        lines.append(line)
    return "\n\n".join(lines)


def send_to_slack(message: str):
    if not SLACK_WEBHOOK_URL:
        logger.error("SLACK_WEBHOOK_URL environment variable not set")
        return
    payload = {"text": message}
    resp = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    if resp.status_code != 200:
        logger.error("Slack webhook failed with status %s: %s", resp.status_code, resp.text)
    else:
        logger.info("Message sent to Slack")


def main():
    trends = fetch_trends(KEYWORDS)
    message = format_message(trends)
    print(message)
    send_to_slack(message)


if __name__ == "__main__":
    main()
