FROM python:3.10
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y docker.io
RUN pip install --upgrade pip && pip install -r requirements.txt
EXPOSE 8501
CMD ["bash", "start.sh"]
