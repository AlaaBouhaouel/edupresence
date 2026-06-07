release: python manage.py migrate --no-input
web: gunicorn edupresence.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
