from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        # State is already correct in 0001_initial (day, start_time, end_time).
        # This only fixes the actual DB table which was created from an older schema.
        migrations.RunSQL(
            sql="""
            DROP TABLE IF EXISTS app_classschedule;
            CREATE TABLE app_classschedule (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                day        VARCHAR(3) NOT NULL,
                start_time TIME NOT NULL,
                end_time   TIME NOT NULL,
                classe_id  INTEGER NOT NULL REFERENCES app_class(id) DEFERRABLE INITIALLY DEFERRED,
                teacher_id INTEGER NOT NULL REFERENCES app_teacher(id) DEFERRABLE INITIALLY DEFERRED,
                UNIQUE (teacher_id, classe_id, day)
            );
            """,
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[],
        ),
    ]
