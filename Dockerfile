FROM python:3.12-slim

WORKDIR /app

# 只复制运行所需文件（不复制 _data，让它首次启动时自动播种 50 条 Prompt）
COPY server.py .
COPY ai_ad_director_v31.html ./index.html

EXPOSE 8081

CMD ["python", "server.py"]
