import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import yaml
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError


# =====================
# 路径配置
# =====================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LATEX_TEMPLATE_DIR = BASE_DIR / "latex" / "input_template"
LATEX_JOBS_DIR = BASE_DIR / "latex" / "jobs"

JOBS_XLSX = DATA_DIR / "jobs.xlsx"
PROFILE_YAML = DATA_DIR / "profile.yaml"
PROMPT_TXT = DATA_DIR / "prompt.txt"

MODEL_NAME = "gpt-5.4-mini"


# =====================
# 初始化 OpenAI
# =====================
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("没有找到 OPENAI_API_KEY，请先在 .env 文件里配置")

client = OpenAI(api_key=api_key)


# =====================
# 工具函数
# =====================
def read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def load_profile_as_text() -> str:
    """把 profile.yaml 转成可读文本，塞进 {{INFO}}"""
    if not PROFILE_YAML.exists():
        raise FileNotFoundError(f"profile.yaml 不存在: {PROFILE_YAML}")

    with open(PROFILE_YAML, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    # 这里直接保留 YAML 风格文本，给模型更自然
    return yaml.safe_dump(
        profile,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False
    )


def load_job_by_id(job_id: str) -> tuple[pd.DataFrame, int, dict]:
    if not JOBS_XLSX.exists():
        raise FileNotFoundError(f"jobs.xlsx 不存在: {JOBS_XLSX}")

    df = pd.read_excel(JOBS_XLSX, dtype=str).fillna("")
    matched_idx = df.index[df["Job_ID"].astype(str) == str(job_id)].tolist()

    if not matched_idx:
        raise ValueError(f"Job_ID {job_id} 不存在于 {JOBS_XLSX}")

    row_idx = matched_idx[0]
    row = df.loc[row_idx].to_dict()
    return df, row_idx, row


def validate_job_for_generation(job: dict) -> None:
    status = str(job.get("Status", "")).strip()

    if status == "Invalid_Link":
        raise ValueError("该岗位记录状态为 Invalid_Link，不能生成 CV")

    if not str(job.get("Job_Title", "")).strip():
        raise ValueError("Job_Title 为空，无法生成 prompt")

    if not str(job.get("JD_Summary", "")).strip():
        raise ValueError("JD_Summary 为空，无法生成 prompt")


def load_latex_modules() -> dict:
    modules = {
        "{{LATEX_EDUCATION}}": read_file(LATEX_TEMPLATE_DIR / "education.tex"),
        "{{LATEX_EXPERIENCE}}": read_file(LATEX_TEMPLATE_DIR / "experience.tex"),
        "{{LATEX_SKILLS}}": read_file(LATEX_TEMPLATE_DIR / "skills.tex"),
        "{{LATEX_PROJECTS}}": "",
    }

    projects_path = LATEX_TEMPLATE_DIR / "projects.tex"
    if projects_path.exists():
        modules["{{LATEX_PROJECTS}}"] = read_file(projects_path)

    return modules


def build_user_prompt(job: dict) -> str:
    prompt_template = read_file(PROMPT_TXT)
    profile_text = load_profile_as_text()
    latex_modules = load_latex_modules()

    final_prompt = prompt_template

    final_prompt = final_prompt.replace("{{INFO}}", profile_text)
    final_prompt = final_prompt.replace("{{JOB_NAME}}", str(job.get("Job_Title", "")))
    final_prompt = final_prompt.replace("{{JOB_LINK}}", str(job.get("Job_URL", "")))
    final_prompt = final_prompt.replace("{{JOB_KEYWORDS}}", str(job.get("Keywords", "")))
    final_prompt = final_prompt.replace("{{JOB_DESCRIPTION}}", str(job.get("JD_Summary", "")))

    for placeholder, content in latex_modules.items():
        final_prompt = final_prompt.replace(placeholder, content)

    return final_prompt


SYSTEM_PROMPT = r"""
You are a senior LaTeX formatting expert and CV optimization consultant.
You must follow the user's template instructions exactly.

Core rules:
- Only replace placeholders with relevant content from the provided asset library.
- Do not modify LaTeX structure, commands, environments, or fixed content.
- Do not invent skills, achievements, publications, or experience.
- Return only final LaTeX content, with no markdown fences.
- Use \& for ampersand, never \\&.
- Keep the output ready for XeLaTeX compilation.
- Before outputting, verify all placeholders are filled and formatting is valid.
""".strip()


def call_cv_api(user_prompt: str, model: str = MODEL_NAME) -> str:
    if not user_prompt.strip():
        raise ValueError("user_prompt 为空")

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.output_text
    if not text or not text.strip():
        raise ValueError("API 返回为空")

    return text


def sanitize_latex_content(tex: str) -> str:
    """
    修正常见的双重转义和 markdown 包裹问题
    """
    tex = tex.replace("```latex", "").replace("```tex", "").replace("```", "")
    tex = tex.replace("\\\\&", "\\&")
    tex = tex.replace("\\\\%", "\\%")
    tex = tex.replace("\\\\#", "\\#")
    tex = tex.replace("\\\\_", "\\_")
    tex = tex.replace("\\\\$", "\\$")
    return tex.strip() + "\n"


def save_job_tex(job_id: str, tex_content: str) -> Path:
    LATEX_JOBS_DIR.mkdir(parents=True, exist_ok=True)
    tex_path = LATEX_JOBS_DIR / f"job_{job_id}.tex"
    tex_path.write_text(tex_content, encoding="utf-8")
    return tex_path


def update_excel_success(df: pd.DataFrame, row_idx: int, tex_path: Path) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    old_notes = str(df.loc[row_idx, "Notes"]) if "Notes" in df.columns else ""
    new_note = "[CV Generation] generated from prompt.txt + LaTeX templates + profile.yaml"
    merged_notes = new_note if not old_notes else f"{old_notes}\n{new_note}"

    df.loc[row_idx, "CV_Tex_Path"] = str(tex_path)
    df.loc[row_idx, "Status"] = "CV_Generated"
    df.loc[row_idx, "Last_Update"] = now_str

    if "Notes" in df.columns:
        df.loc[row_idx, "Notes"] = merged_notes

    df.to_excel(JOBS_XLSX, index=False)


def update_excel_failure(df: pd.DataFrame, row_idx: int, error_message: str) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    old_notes = str(df.loc[row_idx, "Notes"]) if "Notes" in df.columns else ""
    new_note = f"[CV Generation Error] {error_message}"
    merged_notes = new_note if not old_notes else f"{old_notes}\n{new_note}"

    df.loc[row_idx, "Status"] = "CV_Error"
    df.loc[row_idx, "Last_Update"] = now_str

    if "Notes" in df.columns:
        df.loc[row_idx, "Notes"] = merged_notes

    df.to_excel(JOBS_XLSX, index=False)


def save_debug_prompt(job_id: str, prompt_text: str) -> Path:
    debug_dir = BASE_DIR / "prompt"
    debug_dir.mkdir(parents=True, exist_ok=True)
    debug_path = debug_dir / f"job_{job_id}.txt"
    debug_path.write_text(prompt_text, encoding="utf-8")
    return debug_path


def main():
    if len(sys.argv) < 2:
        print("用法: python generate_cv_for_job.py <Job_ID>")
        sys.exit(1)

    job_id = str(sys.argv[1]).strip()

    print("1. 读取岗位信息...")
    df, row_idx, job = load_job_by_id(job_id)

    print("2. 检查岗位状态...")
    validate_job_for_generation(job)

    print("3. 组装 prompt...")
    user_prompt = build_user_prompt(job)
    debug_path = save_debug_prompt(job_id, user_prompt)
    print("已保存调试 prompt:", debug_path)

    print("4. 调用 OpenAI API...")
    try:
        raw_tex = call_cv_api(user_prompt, model=MODEL_NAME)
        clean_tex = sanitize_latex_content(raw_tex)
    except RateLimitError as e:
        error_message = f"OpenAI quota/rate error: {str(e)}"
        print("生成失败:", error_message)
        update_excel_failure(df, row_idx, error_message)
        sys.exit(1)
    except Exception as e:
        error_message = f"OpenAI generation error: {str(e)}"
        print("生成失败:", error_message)
        update_excel_failure(df, row_idx, error_message)
        sys.exit(1)

    print("5. 保存 tex 文件...")
    tex_path = save_job_tex(job_id, clean_tex)

    print("6. 更新 Excel...")
    update_excel_success(df, row_idx, tex_path)

    print("完成 ✅")
    print("生成文件:", tex_path)


if __name__ == "__main__":
    main()