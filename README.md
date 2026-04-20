# AI CV Generation Pipeline
A Python-based workflow for generating job-tailored LaTeX resumes from job descriptions.
## Workflow
```text
JD URL
  ↓
ingest_job.py
  ↓
Extract job info → jobs.xlsx
  ↓
generate_cv_for_job.py <Job_ID>
  ↓
Load profile + prompt + LaTeX templates
  ↓
Call API
  ↓
Generate job_<Job_ID>.tex
  ↓
Compile PDF
```
--- 
LLM Pipeline 设计（两阶段调用）

整个 JD → CV 的流程中，LLM API 被设计为两个明确分工的调用阶段，而不是单次生成：

第一阶段：JD 解析与结构化（Job Ingestion）

在获取岗位 JD 后，首先调用模型对原始文本进行解析，提取关键信息并写入 jobs.xlsx，包括：
	•	公司名称
	•	岗位名称
	•	岗位摘要
	•	关键词标签
	•	岗位类型分类

这一步的目的不是生成内容，而是将非结构化 JD 转换为结构化数据，方便：
	•	人工快速浏览与筛选岗位
	•	后续投递状态管理（tracking / notes / follow-ups）
	•	为后续 CV 生成提供稳定输入

👉 本质上，这一步是在构建一个可管理的岗位索引层（job index layer）。

⸻

第二阶段：定制化 CV 生成（LaTeX Generation）

在选定某个岗位后，系统会基于该岗位的结构化信息，进行第二次 API 调用，用于生成对应的 LaTeX 内容。

这一阶段的特点是：
	•	每个 job ID 对应独立 prompt（保存在 prompt/job_x.txt 中）
	•	prompt 由 profile + JD 信息 + 模板模块拼接而成
	•	模型只负责填充 placeholder，而不生成自由结构

同时，通过 prompt 约束实现对输出的严格控制：
	•	保持 LaTeX 模板结构不变
	•	只替换指定字段（placeholder）
	•	禁止输出解释性文本或 markdown
	•	控制转义与格式，避免编译错误

👉 这一阶段的核心目标是：

在高约束格式（LaTeX）下，实现稳定、可编译的内容生成。

⸻

设计动机

将流程拆分为两次 API 调用，而不是一次完成，有几个原因：
	1.	解耦数据处理与内容生成
JD 解析和 CV 生成是两类不同问题，分开处理更稳定
	2.	提高可控性与可调试性
每个阶段都有独立输入输出，方便定位问题与迭代
	3.	支持人工参与与产品化流程
jobs.xlsx 作为中间层，使系统不仅是生成工具，也具备管理能力
	4.	降低生成复杂度，提升稳定性
将任务拆解后，第二阶段可以专注于结构化填充，从而减少模型失控

⸻

总结

该项目并不是简单调用一次 LLM 完成任务，而是设计了一个两阶段的 LLM workflow：
	•	第一阶段：结构化（理解 JD）
	•	第二阶段：生成（输出 CV）

这种设计使得系统在可控性、稳定性和可扩展性上都有明显提升。
---
## Usage

1. Prepare the following files

* data/profile.yaml — your personal profile
* data/prompt.txt — prompt rules connecting profile data and LaTeX templates
* latex/basic/photo0.jpg — replace with your own photo
* latex/basic/header.tex — replace with your own personal information
* latex/input_template/education.tex — customize education template
* latex/input_template/experience.tex
* latex/input_template/skills.tex
* latex/input_template/projects.tex

2. Add your OpenAI API key to .env

OPENAI_API_KEY=your_api_key_here

3. Create jobs.xlsx

Before ingestion, create data/jobs.xlsx.

You can initialize it with:

* jobs_xlsx_creat.ipynb

4. Ingest a job description

Run the following inside the scripts directory:
```bash
cd scripts
python ingest_job.py "JOB_URL"
```
5. Generate job-specific LaTeX content
```bash
python generate_cv_for_job.py <Job_ID>
```
6. Compile the final PDF

Then switch to the latex directory:
```bash
cd ../latex
python cv_job_id_auto.py <Job_ID>
```
## Stack

* Python
* OpenAI API
* LaTeX
* Pandas / OpenPyXL
* YAML

## Notes

Use anonymized demo data for public upload.

Do not upload:

* real profile.yaml
* real jobs.xlsx
* .env
* generated private application files

## Example
```bash
cd scripts
python ingest_job.py "https://example.com/job"
python generate_cv_for_job.py 1
cd ../latex
python cv_job_id_auto.py 1
```
