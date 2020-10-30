# Generated by Django 3.0.4 on 2020-10-27 12:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mails", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="due",
            name="mail",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="dues",
                to="mails.Mail",
            ),
        ),
    ]