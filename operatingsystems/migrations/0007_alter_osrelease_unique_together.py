# Generated by Django 4.2.19 on 2025-02-26 16:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operatingsystems', '0006_osrelease_cpe_name_osvariant_codename'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='osrelease',
            unique_together={('name', 'codename', 'cpe_name')},
        ),
    ]
