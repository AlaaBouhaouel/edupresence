from django.contrib import admin
from .models import (
    Teacher, Class, ClassSchedule,
    Student, Enrollment, AttendanceSession, Presence,
)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'uid', 'email', 'matiere', 'date_joined')
    search_fields = ('name', 'email', 'uid')


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'classe', 'day', 'start_time', 'end_time')
    list_filter = ('classe', 'teacher', 'day')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'uid', 'email', 'date_joined')
    search_fields = ('name', 'email', 'uid')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'classe', 'date_enrolled')
    list_filter = ('classe',)
    search_fields = ('student__name',)


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('classe', 'teacher', 'date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'classe', 'teacher')


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'status', 'timestamp')
    list_filter = ('status', 'session__classe')
    search_fields = ('student__name',)
