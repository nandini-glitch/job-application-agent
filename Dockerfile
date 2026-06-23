FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1

# Install system dependencies for Xvfb + Chromium
RUN apt-get update && apt-get install -y \
    xvfb \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency files first (better Docker layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Install Playwright's Chromium browser
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# Copy the rest of the app
COPY . .

# Expose Streamlit's port
EXPOSE 8501

# Run Streamlit wrapped in Xvfb's virtual display
RUN mkdir -p /root/.streamlit && \
    echo "[general]" > /root/.streamlit/credentials.toml && \
    echo "email = \"\"" >> /root/.streamlit/credentials.toml
CMD xvfb-run --auto-servernum --server-args="-screen 0 1280x800x24" uv run streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0