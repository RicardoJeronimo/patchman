# Generated by Django 4.2.19 on 2025-03-04 22:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operatingsystems', '0007_alter_osrelease_unique_together'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='osrelease',
            options={'ordering': ['name'], 'verbose_name': 'Operating System Release', 'verbose_name_plural': 'Operating System Releases'},
        ),
        migrations.AlterModelOptions(
            name='osvariant',
            options={'ordering': ['name'], 'verbose_name': 'Operating System Variant', 'verbose_name_plural': 'Operating System Variants'},
        ),
    ]
