#!/usr/bin/env bash
set -o errexit

echo "Collecting static files..."
python manage.py collectstatic --noinput
