# Generated by Django 4.2.19 on 2025-03-04 22:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hosts', '0007_alter_host_tags'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='host',
            options={'ordering': ['hostname'], 'verbose_name': 'Host', 'verbose_name_plural': 'Hosts'},
        ),
    ]
