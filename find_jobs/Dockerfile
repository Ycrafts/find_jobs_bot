FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Default runs both bot (main.py with scheduler disabled) and worker together
ENV APP_MODE=all

CMD ["python", "entrypoint.py"] 