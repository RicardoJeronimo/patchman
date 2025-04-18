# Generated by Django 4.2.19 on 2025-03-10 23:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0005_alter_package_packagetype'),
        ('errata', '0006_alter_erratum_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='erratum',
            name='fixed_packages',
            field=models.ManyToManyField(blank=True, related_name='provides_fix_in_erratum', to='packages.package'),
        ),
    ]
