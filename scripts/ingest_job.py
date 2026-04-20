import os
import sys
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright


# =====================
# 路径配置
# =====================
BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_XLSX = BASE_DIR / "data" / "jobs.xlsx"

# 可按需调整
MODEL_NAME = "gpt-5.4-mini"
MAX_TEXT_LEN = 20000


# =====================
# 初始化 OpenAI
# =====================
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("没有找到 OPENAI_API_KEY，请先在 .env 文件里配置")

client = OpenAI(api_key=api_key)


# =====================
# 判断页面是否像 JD
# =====================
def judge_jd_content(text: str) -> tuple[str, str]:
    text_lower = text.lower()

    invalid_signals = [
        "job expired",
        "position closed",
        "job not found",
        "not found",
        "access denied",
        "sign in",
        "login",
        "verify you are human",
        "page not found",
        "this job is no longer available",
        "职位已下线",
        "岗位已关闭",
        "页面不存在",
        "请登录",
        "扫码登录",
        "注册登录"
    ]

    jd_signals = [
        "responsibilities",
        "requirements",
        "qualifications",
        "about the role",
        "what you will do",
        "who you are",
        "preferred qualifications",
        "minimum qualifications",
        "岗位职责",
        "任职要求",
        "岗位要求",
        "职位描述",
        "你将负责",
        "我们希望你",
        "职位要求",
        "工作职责"
    ]

    if len(text.strip()) < 300:
        return "jd_invalid", "Text too short"

    for s in invalid_signals:
        if s in text_lower:
            return "jd_invalid", f"Invalid page signal: {s}"

    hit_count = sum(1 for s in jd_signals if s in text_lower)

    if hit_count >= 2:
        return "jd_ok", f"Detected {hit_count} JD signals"
    if hit_count == 1:
        return "jd_suspect", "Only 1 JD signal detected"
    return "jd_invalid", "No clear JD signal found"


# =====================
# requests 方式抓取
# =====================
def fetch_jd_text_with_requests(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20,
            allow_redirects=True
        )

        final_url = response.url
        status_code = response.status_code

        if status_code != 200:
            return {
                "success": False,
                "link_status": "broken",
                "content_status": "jd_invalid",
                "final_url": final_url,
                "text": "",
                "note": f"HTTP {status_code}",
                "fetch_method": "requests"
            }

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.extract()

        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)

        link_status = "redirected" if final_url != url else "valid"
        content_status, note = judge_jd_content(cleaned_text)

        return {
            "success": content_status == "jd_ok",
            "link_status": link_status,
            "content_status": content_status,
            "final_url": final_url,
            "text": cleaned_text[:MAX_TEXT_LEN],
            "note": note,
            "fetch_method": "requests"
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "link_status": "broken",
            "content_status": "jd_invalid",
            "final_url": url,
            "text": "",
            "note": "Request timeout",
            "fetch_method": "requests"
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "link_status": "broken",
            "content_status": "jd_invalid",
            "final_url": url,
            "text": "",
            "note": f"Request failed: {str(e)}",
            "fetch_method": "requests"
        }


# =====================
# Playwright 方式抓取
# =====================
def fetch_jd_text_with_playwright(url: str) -> dict:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            final_url = page.url
            text = page.locator("body").inner_text()

            browser.close()

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)

        link_status = "redirected" if final_url != url else "valid"
        content_status, note = judge_jd_content(cleaned_text)

        return {
            "success": content_status == "jd_ok",
            "link_status": link_status,
            "content_status": content_status,
            "final_url": final_url,
            "text": cleaned_text[:MAX_TEXT_LEN],
            "note": f"Playwright: {note}",
            "fetch_method": "playwright"
        }

    except Exception as e:
        return {
            "success": False,
            "link_status": "broken",
            "content_status": "jd_invalid",
            "final_url": url,
            "text": "",
            "note": f"Playwright failed: {str(e)}",
            "fetch_method": "playwright"
        }


# =====================
# 根据抓取情况自动选择
# =====================
def fetch_jd_text_auto(url: str) -> dict:
    first_result = fetch_jd_text_with_requests(url)

    print("2. 第一次抓取结果:")
    print(
        first_result["link_status"],
        first_result["content_status"],
        first_result["note"]
    )

    if first_result["success"]:
        return first_result

    print("3. requests 抓取失败，尝试使用 Playwright...")
    second_result = fetch_jd_text_with_playwright(url)

    print("4. Playwright 抓取结果:")
    print(
        second_result["link_status"],
        second_result["content_status"],
        second_result["note"]
    )

    # 只要 Playwright 成功，就优先用它
    if second_result["success"]:
        return second_result

    # 如果都失败，返回 Playwright 结果（通常包含更新的诊断）
    return second_result


# =====================
# 生成下一个 Job_ID
# =====================
def get_next_job_id(df: pd.DataFrame) -> int:
    if df.empty:
        return 1

    numeric_ids = pd.to_numeric(df["Job_ID"], errors="coerce").dropna()
    if numeric_ids.empty:
        return 1

    return int(numeric_ids.max()) + 1


# =====================
# 调 OpenAI 提取岗位信息
# =====================
def extract_job_info_with_llm(job_url: str, jd_text: str) -> dict:
    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {
                "role": "system",
                "content": (
                    "You extract structured job information from a job description. "
                    "Be faithful to the source text. "
                    "Do not invent facts. "
                    "If unclear, use empty string. "
                    "Keywords should be concise and useful for CV tailoring."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Job URL:\n{job_url}\n\n"
                    f"Job Description:\n{jd_text}"
                )
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "job_extract",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "job_title": {"type": "string"},
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "description": {"type": "string"},
                        "job_type": {"type": "string"}
                    },
                    "required": [
                        "company",
                        "job_title",
                        "keywords",
                        "description",
                        "job_type"
                    ],
                    "additionalProperties": False
                }
            }
        }
    )

    return json.loads(response.output_text)


# =====================
# 写入 Excel
# =====================
def append_job_to_excel(fetch_result: dict, job_data: dict | None):
    print("JOBS_XLSX =", JOBS_XLSX)
    print("Exists =", JOBS_XLSX.exists())

    df = pd.read_excel(JOBS_XLSX, dtype=str).fillna("")
    new_job_id = get_next_job_id(df)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_row = {
        "Job_ID": new_job_id,
        "Date_Accessed": now_str,
        "Company": job_data.get("company", "") if job_data else "",
        "Job_URL": fetch_result["final_url"],
        "Job_Title": job_data.get("job_title", "") if job_data else "",
        "Keywords": ", ".join(job_data.get("keywords", [])) if job_data else "",
        "JD_Summary": job_data.get("description", "") if job_data else "",
        "Job_Type": job_data.get("job_type", "") if job_data else "",
        "Link_Status": fetch_result["link_status"],
        "Content_Status": fetch_result["content_status"],
        "Fetch_Note": f'{fetch_result["fetch_method"]}: {fetch_result["note"]}',
        "Status": "Imported" if fetch_result["success"] else "Invalid_Link",
        "Applied_Date": "",
        "Next_Action": "Generate CV" if fetch_result["success"] else "",
        "Next_Action_Date": "",
        "CV_Tex_Path": "",
        "CV_PDF_Path": "",
        "Notes": "",
        "Last_Update": now_str
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(JOBS_XLSX, index=False)

    print(f"已写入 {JOBS_XLSX}")
    print(f"Job_ID: {new_job_id}")
    print(f"Link_Status: {new_row['Link_Status']}")
    print(f"Content_Status: {new_row['Content_Status']}")
    print(f"Status: {new_row['Status']}")
    print(f"Fetch_Note: {new_row['Fetch_Note']}")


# =====================
# 主程序
# =====================
def main():
    if len(sys.argv) < 2:
        print('用法: python ingest_job.py "JD_URL"')
        sys.exit(1)

    job_url = sys.argv[1]

    print("1. 正在抓取页面...")
    fetch_result = fetch_jd_text_auto(job_url)

    if fetch_result["success"]:
        print("5. 正在调用 OpenAI 提取岗位信息...")
        job_data = extract_job_info_with_llm(job_url, fetch_result["text"])
    else:
        print("5. 链接无效或不是标准 JD，跳过 API 提取")
        job_data = None

    print("6. 正在写入 Excel...")
    append_job_to_excel(fetch_result, job_data)

    print("完成 ✅")


if __name__ == "__main__":
    main()