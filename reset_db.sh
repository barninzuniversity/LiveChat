#!/bin/bash
# Script to reset all users and posts in the application

# Check if we want to keep superusers
if [ "$1" == "--keep-superuser" ]; then
  python manage.py purge_data --keep-superuser
else
  python manage.py purge_data
fi

echo "Database reset complete!" 