可以，我帮你把这版 README 改成更自然、适合直接放 GitHub 的版本。
我保留你的内容和流程，只把语言整理顺一点。

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