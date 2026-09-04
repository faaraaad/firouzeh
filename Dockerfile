FROM python:3.12-slim

# Prevents Python from writing .pyc files and enables unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (leverages Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . .

# Collect static files (requires SECRET_KEY; use a dummy value at build time only)
RUN DJANGO_SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

EXPOSE 9000

# Run migrations then start gunicorn on port 9000 with 4 workers
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn firouzeh.wsgi:application --bind 0.0.0.0:9000 --workers 4 --timeout 120 --access-logfile -"]
