FROM python:3.14-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY scripts/ scripts/

CMD ["uv", "run", "python", "scripts/load_data.py"]
