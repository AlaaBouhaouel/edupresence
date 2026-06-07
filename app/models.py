from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    uid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    matiere = models.CharField(max_length=100)
    date_joined = models.DateField(default=timezone.now)

    def __str__(self):
        return self.name


class Class(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    teachers = models.ManyToManyField(Teacher, through='ClassSchedule')

    def __str__(self):
        return self.name


class ClassSchedule(models.Model):
    DAYS = [
        ('MON', 'Lundi'),
        ('TUE', 'Mardi'),
        ('WED', 'Mercredi'),
        ('THU', 'Jeudi'),
        ('FRI', 'Vendredi'),
        ('SAT', 'Samedi'),
    ]

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    classe = models.ForeignKey(Class, on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ['teacher', 'classe', 'day']

    def clean(self):
        # During partial object creation (before form fields are assigned),
        # avoid running overlap queries with None values.
        if not self.classe_id or not self.day or not self.start_time or not self.end_time:
            return

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Schedule start time must be earlier than end time.")

        overlapping = ClassSchedule.objects.filter(
            classe=self.classe,
            day=self.day,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError(
                "This class already has another teaching schedule overlapping this time."
            )

        teacher_overlapping = ClassSchedule.objects.filter(
            teacher=self.teacher,
            day=self.day,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        if teacher_overlapping.exists():
            raise ValidationError(
                "This teacher already has another class overlapping this time."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.teacher.name} - {self.classe.name} - {self.get_day_display()} {self.start_time}-{self.end_time}"


class Student(models.Model):
    uid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    date_joined = models.DateField(default=timezone.now)

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    classe = models.ForeignKey(Class, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=timezone.now)

    class Meta:
        unique_together = ['student', 'classe']

    def clean(self):
        if Enrollment.objects.filter(student=self.student).exclude(pk=self.pk).exists():
            raise ValidationError("A student can only be enrolled in one class.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.name} -> {self.classe.name}"


class AttendanceSession(models.Model):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    STATUS_CHOICES = [(OPEN, 'Open'), (CLOSED, 'Closed')]

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    classe = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=OPEN)

    def __str__(self):
        return f"{self.classe.name} - {self.date} [{self.status}]"


class Presence(models.Model):
    PRESENT = 'present'
    ABSENT = 'absent'
    STATUS_CHOICES = [(PRESENT, 'Present'), (ABSENT, 'Absent')]

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PRESENT)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session', 'student']

    def __str__(self):
        return f"{self.student.name} - {self.session} - {self.status}"
