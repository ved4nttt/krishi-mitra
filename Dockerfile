# Use official Python lightweight image
FROM python:3.10-slim

# Install FFmpeg (Required for WhatsApp audio processing)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your project files into the container
COPY . .

# Start the FastAPI server on port 10000 (Render's default)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]