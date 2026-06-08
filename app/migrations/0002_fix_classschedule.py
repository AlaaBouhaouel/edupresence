from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        # No-op: the original raw SQL used SQLite-only AUTOINCREMENT syntax.
        # The table is correctly created by 0001_initial via Django's ORM.
    ]
