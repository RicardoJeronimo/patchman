# Generated by Django 4.2.19 on 2025-02-11 03:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cve',
            options={'ordering': ('cve_id',)},
        ),
    ]
