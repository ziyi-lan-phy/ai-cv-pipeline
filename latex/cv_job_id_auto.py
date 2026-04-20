import shutil
import os
import sys

template = "cv_job_id.tex"
os.makedirs("jobs", exist_ok=True)

# 从命令行读取数字参数
# 例如 python job_latex_auto.py 1 2 3
nums = sys.argv[1:]  # 这是一个列表 ['1', '2', '3']

# 根据数字生成 job 名称
jobs = [f"job_{num}" for num in nums]

for job in jobs:
    new_cv_name = f"CV_{job}.tex"
    
    # 复制模板
    shutil.copy(template, new_cv_name)
    
    # 替换模板里的 Job_ID
    with open(new_cv_name, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("Job_ID", job)
    with open(new_cv_name, "w", encoding="utf-8") as f:
        f.write(content)
    os.system(f"xelatex -interaction=nonstopmode {new_cv_name}")
    print(f"Generated: {new_cv_name}")
