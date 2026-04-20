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
## Usage

1. Prepare the following files:
    * data/profile.yaml # 你自己的资料
    * data/prompt.txt # 衔接资料和latex格式
    * latex/basic/photo0.jpg # 替换你的照片
    * latex/basic/header.tex # 替换你的个人信息
    * latex/input_template/education.tex # 替换教育title内容，下同
    * latex/input_template/experience.tex
    * latex/input_template/skills.tex
    * latex/input_template/projects.tex

2. Add your OpenAI API key to .env:
```bash
OPENAI_API_KEY=your_api_key_here
```
3. Ingest a job description:

之前需要在`data`创建`jobs.xlsx`，可以通过`jobs_xlsx_creat.ipynb`初始设置

以下内容在`scripts`目录里继续
```bash
cd scripts
```

```bash
python ingest_job.py "JOB_URL" 
```
4. Generate job-specific LaTeX content:
```bash
python generate_cv_for_job.py <Job_ID>
```
5. Compile the final PDF:
以下内容在`latex`目录里继续
```bash
cd latex
```
```bash
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
