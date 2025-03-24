# Generated by Django 5.1.2 on 2025-03-18 04:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_profile_created_at_profile_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='messages/files/'),
        ),
        migrations.AddField(
            model_name='message',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='messages/images/'),
        ),
        migrations.AlterField(
            model_name='message',
            name='content',
            field=models.TextField(blank=True),
        ),
    ]
