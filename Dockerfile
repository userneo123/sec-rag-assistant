FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (separate layer so Docker caches this step
# and doesn't reinstall everything just because app code changed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code
COPY diligence_assistant/ ./diligence_assistant/

# Azure App Service (Linux, container-based) expects the container to
# listen on port 8000 unless configured otherwise via WEBSITES_PORT.
EXPOSE 8000

CMD ["uvicorn", "diligence_assistant.api:app", "--host", "0.0.0.0", "--port", "8000"]
