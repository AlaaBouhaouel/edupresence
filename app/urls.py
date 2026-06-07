from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.sign_in, name='signin'),
    path('signout/', views.sign_out, name='signout'),
    path('forget_password/', views.forget_password, name='forget_password'),

    # Admin
    path('admin_home/', views.admin_home, name='admin_home'),
    path('admin_classe/', views.admin_classe, name='admin_classe'),
    path('admin_student/', views.admin_student, name='admin_student'),
    path('admin_teacher/', views.admin_teacher, name='admin_teacher'),

    # Teacher pages
    path('teacher_home/<int:teacher_id>/', views.teacher_home, name='teacher_home'),
    path('teacher_classe/<int:teacher_id>/', views.teacher_classe, name='teacher_classe'),
    path('teacher_student/<int:teacher_id>/', views.teacher_student, name='teacher_student'),

    # Teacher CRUD
    path('manage_teacher/', views.manage_teacher, name='manage_teacher'),
    path('manage_teacher/add/', views.add_teacher, name='add_teacher'),
    path('manage_teacher/<int:teacher_id>/edit/', views.edit_teacher, name='edit_teacher'),
    path('manage_teacher/<int:teacher_id>/delete/', views.delete_teacher, name='delete_teacher'),
    path('manage_teacher/<int:teacher_id>/account/', views.create_teacher_account, name='create_teacher_account'),

    # Student CRUD
    path('manage_student/', views.manage_student, name='manage_student'),
    path('manage_student/add/', views.add_student, name='add_student'),
    path('manage_student/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('manage_student/<int:student_id>/delete/', views.delete_student, name='delete_student'),

    # Classe CRUD
    path('manage_classe/<int:classe_id>/', views.manage_classe, name='manage_classe'),
    path('manage_classe/add/', views.add_classe, name='add_classe'),
    path('manage_classe/<int:classe_id>/edit/', views.edit_classe, name='edit_classe'),
    path('manage_classe/<int:classe_id>/delete/', views.delete_classe, name='delete_classe'),

    # Attendance
    path('attendance/session/', views.attendance_session, name='attendance_session'),
    path('attendance/dashboard/<int:session_id>/', views.attendance_dashboard, name='attendance_dashboard'),
    path('attendance/register/', views.attendance_register, name='attendance_register'),

    # Firebase webhook (no CSRF — called by Firebase Cloud Function)
    path('api/scan/', views.scan_webhook, name='scan_webhook'),
]
