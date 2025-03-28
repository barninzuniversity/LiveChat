# Generated by Django 5.1.2 on 2025-03-16 23:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_post_image_post_video'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='blocked_users',
            field=models.ManyToManyField(blank=True, related_name='blocked_by', to='chat.profile'),
        ),
        migrations.CreateModel(
            name='BlockedPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blocked_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocked_by', to='chat.post')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocked_posts', to='chat.profile')),
            ],
            options={
                'unique_together': {('user', 'post')},
            },
        ),
    ]
