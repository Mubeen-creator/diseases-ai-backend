FROM python:3.9-slim

WORKDIR /code

# Copy requirements first for better caching
COPY requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy application code
COPY . /code

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]