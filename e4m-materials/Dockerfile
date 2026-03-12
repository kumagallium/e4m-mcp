FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*
COPY e4m-materials/pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .
COPY e4m-materials/src/ src/
RUN pip install --no-cache-dir -e .
ENV TRANSPORT=sse
EXPOSE 8000
CMD ["python", "-m", "e4m_materials", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
