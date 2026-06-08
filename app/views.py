import json
import secrets
import string
from datetime import date as dt_date
from urllib.parse import quote_plus
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from django.db.models import Count, Q
from django.core.exceptions import ValidationError


def csrf_failure(request, reason=''):
    return HttpResponseForbidden(
        render(request, 'csrf_failure.html', {'reason': reason}).content,
        content_type='text/html',
    )
from .models import (
    Teacher, Class, ClassSchedule,
    Student, Enrollment, AttendanceSession, Presence
)
from . import firebase_utils


# ── GENERAL ───────────────────────────────────────────────────────────────────

def index(request):
    return render(request, 'index.html')


def settings(request):
    return render(request, 'settings.html')


def sign_in(request):
    if request.user.is_authenticated:
        return _redirect_after_login(request.user)
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password'],
        )
        if user:
            login(request, user)
            return _redirect_after_login(user)
        return render(request, 'signin.html', {'error': 'Identifiants incorrects.'})
    return render(request, 'signin.html')


def sign_out(request):
    logout(request)
    return render(request, 'logout.html')


def _redirect_after_login(user):
    teacher = Teacher.objects.filter(user=user).first()
    if teacher and teacher.id:
        return redirect('teacher_home', teacher_id=teacher.id)
    return redirect('admin_home')


def forget_password(request):
    return render(request, 'forgetpass.html')


# ── ADMIN VIEWS ───────────────────────────────────────────────────────────────

def admin_home(request):
    context = {
        'teachers': Teacher.objects.all(),
        'students': Student.objects.all(),
        'classes': Class.objects.all(),
        'students_count': Student.objects.count(),
        'teacher_count': Teacher.objects.count(),
        'classes_count': Class.objects.count(),
    }
    return render(request, 'admin_home.html', context)


def admin_classe(request):
    context = {
        'teachers': Teacher.objects.all(),
        'students': Student.objects.all(),
        'classes': Class.objects.all(),
    }
    return render(request, 'admin_classe.html', context)


def admin_student(request):
    context = {'students': Student.objects.all()}
    return render(request, 'admin_student.html', context)


def admin_teacher(request):
    context = {'teachers': Teacher.objects.all()}
    return render(request, 'admin_teacher.html', context)


# ── TEACHER HOME ──────────────────────────────────────────────────────────────

def teacher_home(request, teacher_id):
    teacher = Teacher.objects.get(id=teacher_id)
    schedules = ClassSchedule.objects.filter(teacher=teacher).select_related('classe')
    classes_list = Class.objects.filter(teachers=teacher)
    classes_with_students = []
    for cls in classes_list:
        students = Student.objects.filter(enrollment__classe=cls).annotate(
            absence_count=Count('presence', filter=Q(presence__status='absent')),
            presence_count=Count('presence', filter=Q(presence__status='present'))

        )
        classes_with_students.append({'classe': cls, 'students': students})

    context = {
        'teacher': teacher,
        'schedules': schedules,
        'classes_with_students': classes_with_students,
        'students_count': Student.objects.filter(enrollment__classe__in=classes_list).distinct().count(),
        'classes_count': classes_list.count(),
    }
    return render(request, 'teacher_home.html', context)


def teacher_classe(request, teacher_id):
    teacher = Teacher.objects.get(id=teacher_id)
    context = {
        'teacher': teacher,
        'classes': Class.objects.filter(teachers=teacher),
    }
    return render(request, 'teacher_classe.html', context)


def teacher_student(request, teacher_id):
    teacher = Teacher.objects.get(id=teacher_id)
    classes_list = Class.objects.filter(teachers=teacher)
    context = {
        'teacher': teacher,
        'students': Student.objects.filter(enrollment__classe__in=classes_list).distinct(),
    }
    return render(request, 'teacher_student.html', context)


# ── TEACHER CRUD ──────────────────────────────────────────────────────────────

def manage_teacher(request):
    context = {'teachers': Teacher.objects.all()}
    return render(request, 'manage_teacher.html', context)


def add_teacher(request):
    if request.method == 'POST':
        uid = request.POST.get('uid', '').strip().upper()
        Teacher.objects.create(
            uid=uid or None,
            name=request.POST.get('name', ''),
            email=request.POST.get('email', ''),
            matiere=request.POST.get('matiere', ''),
        )
        return redirect('manage_teacher')
    return render(request, 'form_teacher.html', {'action': 'Ajouter'})


def edit_teacher(request, teacher_id):
    teacher = Teacher.objects.get(id=teacher_id)
    if request.method == 'POST':
        teacher.name = request.POST['name']
        teacher.email = request.POST['email']
        teacher.matiere = request.POST['matiere']
        teacher.save()
        return redirect('manage_teacher')
    return render(request, 'form_teacher.html', {'teacher': teacher, 'action': 'Modifier'})


def delete_teacher(request, teacher_id):
    if request.method == 'POST':
        Teacher.objects.filter(id=teacher_id).delete()
    return redirect('manage_teacher')


def _generate_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_teacher_account(request, teacher_id):
    teacher = Teacher.objects.get(id=teacher_id)

    if teacher.user:
        # Already has an account — reset password instead
        temp_password = _generate_password()
        teacher.user.set_password(temp_password)
        teacher.user.save()
        return render(request, 'teacher_account_created.html', {
            'teacher': teacher,
            'username': teacher.user.username,
            'temp_password': temp_password,
            'reset': True,
        })

    # Build a unique username from teacher name
    base = teacher.name.lower().replace(' ', '.')
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1

    temp_password = _generate_password()
    user = User.objects.create_user(
        username=username,
        email=teacher.email,
        password=temp_password,
    )
    teacher.user = user
    teacher.save()

    return render(request, 'teacher_account_created.html', {
        'teacher': teacher,
        'username': username,
        'temp_password': temp_password,
        'reset': False,
    })


# ── STUDENT CRUD ──────────────────────────────────────────────────────────────

def manage_student(request):
    context = {'students': Student.objects.all()}
    return render(request, 'manage_student.html', context)


def student_detail(request, student_id):
    student = Student.objects.get(id=student_id)
    enrollment = Enrollment.objects.filter(student=student).first()
    presences = Presence.objects.filter(student=student).select_related('session__classe', 'session__teacher').order_by('-session__date')

    if not request.user.is_staff:
        teacher = Teacher.objects.filter(user=request.user).first()
        if teacher:
            presences = presences.filter(session__teacher=teacher)

    context = {
        'student': student,
        'enrollment': enrollment,
        'presences': presences,
        'presence_count': presences.filter(status='present').count(),
        'absence_count': presences.filter(status='absent').count(),
    }
    return render(request, 'student_detail.html', context)


def add_student(request):
    if request.method == 'POST':
        uid = request.POST.get('uid', '').strip().upper()
        student = Student.objects.create(
            uid=uid or None,
            name=request.POST.get('name', ''),
            email=request.POST.get('email', ''),
        )
        classe_id = request.POST.get('class_id')
        if classe_id:
            Enrollment.objects.create(
                student=student,
                classe=Class.objects.get(id=classe_id),
            )
        return redirect('manage_student')
    return render(request, 'form_student.html', {
        'classes': Class.objects.all(),
        'action': 'Ajouter',
    })


def edit_student(request, student_id):
    student = Student.objects.get(id=student_id)
    if request.method == 'POST':
        student.name = request.POST['name']
        student.email = request.POST['email']
        student.save()
        classe_id = request.POST.get('class_id')
        if classe_id:
            Enrollment.objects.update_or_create(
                student=student,
                defaults={'classe': Class.objects.get(id=classe_id)},
            )
        return redirect('manage_student')
    enrollment = Enrollment.objects.filter(student=student).first()
    return render(request, 'form_student.html', {
        'student': student,
        'enrollment': enrollment,
        'classes': Class.objects.all(),
        'action': 'Modifier',
    })


def delete_student(request, student_id):
    if request.method == 'POST':
        Student.objects.filter(id=student_id).delete()
    return redirect('manage_student')


# ── CLASSE CRUD ───────────────────────────────────────────────────────────────

def _manage_classe_error_redirect(classe_id, message):
    url = reverse('manage_classe', kwargs={'classe_id': classe_id})
    return redirect(f"{url}?error={quote_plus(message)}")


def manage_classe(request, classe_id):
    classe = Class.objects.get(id=classe_id)
    error_message = request.GET.get('error')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_info':
            name = request.POST.get('name', '').strip()
            if name:
                classe.name = name
                classe.description = request.POST.get('description', '')
                classe.save()

        elif action == 'add_teacher':
            teacher_id = request.POST.get('teacher_id')
            days_list   = request.POST.getlist('days[]')
            starts_list = request.POST.getlist('start_times[]')
            ends_list   = request.POST.getlist('end_times[]')
            if teacher_id and days_list:
                teacher_obj = Teacher.objects.get(id=teacher_id)
                for day, start, end in zip(days_list, starts_list, ends_list):
                    if day and start and end:
                        try:
                            s = ClassSchedule(teacher=teacher_obj, classe=classe,
                                              day=day, start_time=start, end_time=end)
                            s.full_clean()
                            s.save()
                        except ValidationError as exc:
                            msg = exc.messages[0] if exc.messages else "Horaire invalide."
                            return _manage_classe_error_redirect(classe.id, msg)

        elif action == 'remove_teacher':
            ClassSchedule.objects.filter(
                id=request.POST.get('schedule_id'),
                classe=classe,
            ).delete()

        elif action == 'add_student':
            student_id = request.POST.get('student_id')
            if student_id:
                try:
                    Enrollment.objects.update_or_create(
                        student=Student.objects.get(id=student_id),
                        defaults={'classe': classe},
                    )
                except ValidationError as exc:
                    message = exc.messages[0] if exc.messages else "Student enrollment is invalid."
                    return _manage_classe_error_redirect(classe.id, message)

        elif action == 'remove_student':
            Enrollment.objects.filter(
                classe=classe,
                student_id=request.POST.get('student_id'),
            ).delete()

        return redirect('manage_classe', classe_id=classe.id)

    schedules = ClassSchedule.objects.filter(classe=classe).select_related('teacher')
    session_ids = AttendanceSession.objects.filter(classe=classe).values_list('id', flat=True)
    enrolled_students = Student.objects.filter(enrollment__classe=classe).annotate(
        absence_count=Count('presence', filter=Q(
            presence__session__in=session_ids, presence__status='absent'
        )),
        presence_count=Count('presence', filter=Q(
            presence__session__in=session_ids, presence__status='present'
        )),
    )
    assigned_teacher_ids = list(schedules.values_list('teacher_id', flat=True))

    context = {
        'classe': classe,
        'schedules': schedules,
        'students': enrolled_students,
        'available_teachers': Teacher.objects.exclude(id__in=assigned_teacher_ids) if assigned_teacher_ids else Teacher.objects.all(),
        'available_students': Student.objects.filter(enrollment__isnull=True),
        'days': ClassSchedule.DAYS,
        'error_message': error_message,
    }

    
    return render(request, 'manage_classe.html', context)


def classe_register(request, classe_id):
    _DAY_MAP = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
    classe = Class.objects.get(id=classe_id)
    students = list(
        Student.objects.filter(enrollment__classe=classe).order_by('name')
    )
    sessions = list(
        AttendanceSession.objects.filter(classe=classe).order_by('date', 'start_time')
    )
    schedule_map = {
        (s.teacher_id, s.day): s.end_time
        for s in ClassSchedule.objects.filter(classe=classe)
    }
    for s in sessions:
        day_code = _DAY_MAP.get(s.date.weekday())
        s.scheduled_end = schedule_map.get((s.teacher_id, day_code))
    presence_map = {
        (p['student_id'], p['session_id']): p['status']
        for p in Presence.objects.filter(session__classe=classe).values('student_id', 'session_id', 'status')
    }
    rows = []
    for i, student in enumerate(students, start=1):
        cells = [presence_map.get((student.id, s.id)) for s in sessions]
        present = cells.count('present')
        absent = cells.count('absent')
        total = present + absent
        rows.append({
            'num': i,
            'student': student,
            'cells': cells,
            'present': present,
            'absent': absent,
            'rate': round(present / total * 100) if total else 0,
        })
    return render(request, 'classe_register.html', {'classe': classe, 'sessions': sessions, 'rows': rows})


def add_classe(request):
    if request.method == 'POST':
        new_classe = Class.objects.create(
            name=request.POST.get('name', '').strip(),
            description=request.POST.get('description', ''),
        )
        return redirect('manage_classe', classe_id=new_classe.id)
    return render(request, 'form_classe.html', {'action': 'Ajouter'})


def edit_classe(request, classe_id):
    classe = Class.objects.get(id=classe_id)
    error_message = request.GET.get('error')
    if request.method == 'POST':
        classe.name = request.POST['name']
        classe.description = request.POST['description']
        classe.save()

        selected_ids = request.POST.getlist('teachers')
        try:
            with transaction.atomic():
                ClassSchedule.objects.filter(classe=classe).delete()
                for teacher_id in selected_ids:
                    day = request.POST.get(f'day_{teacher_id}')
                    start = request.POST.get(f'start_{teacher_id}')
                    end = request.POST.get(f'end_{teacher_id}')
                    if day and start and end:
                        ClassSchedule.objects.create(
                            classe=classe,
                            teacher=Teacher.objects.get(id=teacher_id),
                            day=day,
                            start_time=start,
                            end_time=end,
                        )
        except ValidationError as exc:
            message = exc.messages[0] if exc.messages else "Invalid teaching schedule."
            url = reverse('edit_classe', kwargs={'classe_id': classe.id})
            return redirect(f"{url}?error={quote_plus(message)}")
        return redirect('manage_classe', classe_id=classe.id)

    schedules = ClassSchedule.objects.filter(classe=classe).select_related('teacher')
    schedule_map = {s.teacher_id: s for s in schedules}
    teacher_data = [
        {
            'teacher': t,
            'is_assigned': t.id in schedule_map,
            'day': schedule_map[t.id].day if t.id in schedule_map else '',
            'start_time': schedule_map[t.id].start_time if t.id in schedule_map else '',
            'end_time': schedule_map[t.id].end_time if t.id in schedule_map else '',
        }
        for t in Teacher.objects.all()
    ]
    return render(request, 'form_classe.html', {
        'classe': classe,
        'teacher_data': teacher_data,
        'error_message': error_message,
        'action': 'Modifier',
    })


def delete_classe(request, classe_id):
    if request.method == 'POST':
        Class.objects.filter(id=classe_id).delete()
    return redirect('admin_home')



from django.shortcuts import render, redirect
from django.http import JsonResponse
import json
from django.http import HttpResponse

# ── ATTENDANCE SESSION ────────────────────────────────────────────────────────

def attendance_session(request):
    if request.method == "POST":
        is_json = "application/json" in request.headers.get("Content-Type", "")
        payload = {}
        if is_json:
            try:
                payload = json.loads(request.body or "{}")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

        uid = (payload.get("uid") if is_json else request.POST.get("uid", "")).strip().upper()

        if not uid:
            if is_json:
                return JsonResponse({"error": "Missing UID"}, status=400)
            return HttpResponse("<h1>ERROR! Missing UID.</h1>", content_type="text/html", status=400)

        teacher = Teacher.objects.filter(uid=uid).first()
        if teacher:
            active_session = AttendanceSession.objects.filter(teacher=teacher, status='OPEN').first()
            if active_session:
                active_session.status = 'CLOSED'
                active_session.end_time = timezone.now()
                active_session.save(update_fields=['status', 'end_time'])
                _mark_absent_students(active_session)
                firebase_utils.update_active_session(None)

                if is_json:
                    return JsonResponse({
                        "action": "session_closed",
                        "session_id": active_session.id,
                        "class": active_session.classe.name,
                    })
                return redirect("attendance_session")

            now = timezone.localtime()
            schedule = _resolve_teacher_schedule(teacher, now)
            if not schedule:
                if is_json:
                    return JsonResponse({"error": "Teacher has no class assigned"}, status=400)
                return HttpResponse("<h1>ERROR! Teacher has no assigned class.</h1>", content_type="text/html", status=400)

            other_open_session = AttendanceSession.objects.filter(status='OPEN').exclude(teacher=teacher).first()
            if other_open_session:
                if is_json:
                    return JsonResponse({"error": "Another session is already open"}, status=409)
                return HttpResponse("<h1>ERROR! Another attendance session is already open.</h1>", content_type="text/html", status=409)

            session = AttendanceSession.objects.create(
                teacher=teacher,
                classe=schedule.classe,
                date=now.date(),
                start_time=timezone.now(),
                status='OPEN',
            )
            firebase_utils.update_active_session(session)

            if is_json:
                return JsonResponse({
                    "action": "session_opened",
                    "session_id": session.id,
                    "class": session.classe.name,
                })
            return redirect("attendance_session")

        student = Student.objects.filter(uid=uid).first()
        if student:
            active_session = AttendanceSession.objects.filter(status='OPEN').first()
            if not active_session:
                if is_json:
                    return JsonResponse({"error": "No active session"}, status=400)
                return HttpResponse("<h1>ERROR! No active attendance session.</h1>", content_type="text/html", status=400)

            if not Enrollment.objects.filter(student=student, classe=active_session.classe).exists():
                if is_json:
                    return JsonResponse({"error": "Student not enrolled in open session class"}, status=400)
                return HttpResponse("<h1>ERROR! Student is not enrolled in the open class.</h1>", content_type="text/html", status=400)

            _, created = Presence.objects.get_or_create(
                session=active_session,
                student=student,
                defaults={'status': 'present'},
            )
            if is_json:
                return JsonResponse({
                    "action": "presence_recorded" if created else "already_recorded",
                    "session_id": active_session.id,
                    "student": student.name,
                })
            return redirect("attendance_session")

        if is_json:
            return JsonResponse({"error": "Unknown UID"}, status=404)
        return HttpResponse("<h1>ERROR! UID not found.</h1>", content_type="text/html", status=404)

    active_session = AttendanceSession.objects.filter(status='OPEN').first()
    recent_sessions = AttendanceSession.objects.order_by('-start_time')[:10]
    context = {
        'active_session': active_session,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'attendance_session.html', context)


def _mark_absent_students(session):
    enrolled_students = Student.objects.filter(enrollment__classe=session.classe)
    present_ids = set(
        Presence.objects.filter(session=session, status='present').values_list('student_id', flat=True)
    )
    absent_presences = [
        Presence(session=session, student=student, status='absent')
        for student in enrolled_students
        if student.id not in present_ids
    ]
    if absent_presences:
        Presence.objects.bulk_create(absent_presences, ignore_conflicts=True)


def _resolve_teacher_schedule(teacher, now):
    day_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}
    today = day_map.get(now.weekday())

    # Preferred: current time slot for today.
    current_schedule = ClassSchedule.objects.filter(
        teacher=teacher,
        day=today,
        start_time__lte=now.time(),
        end_time__gte=now.time(),
    ).select_related('classe').first()
    if current_schedule:
        return current_schedule

    # Fallback for manual/demo scans: nearest class today, else first assigned class.
    today_schedule = ClassSchedule.objects.filter(
        teacher=teacher,
        day=today,
    ).select_related('classe').order_by('start_time').first()
    if today_schedule:
        return today_schedule

    return ClassSchedule.objects.filter(teacher=teacher).select_related('classe').order_by('day', 'start_time').first()


def attendance_dashboard(request, session_id):
    session = AttendanceSession.objects.get(id=session_id)
    can_edit = False
    if request.user.is_authenticated:
        if request.user.is_staff:
            can_edit = True
        else:
            can_edit = Teacher.objects.filter(user=request.user, id=session.teacher_id).exists()

    if request.method == 'POST':
        if not can_edit:
            return JsonResponse({'error': 'Not authorized'}, status=403)

        action = request.POST.get('action')
        student_id = request.POST.get('student_id')
        student = Student.objects.filter(
            id=student_id,
            enrollment__classe=session.classe,
        ).first()
        if student and action in ('mark_present', 'mark_absent'):
            target_status = 'present' if action == 'mark_present' else 'absent'
            Presence.objects.update_or_create(
                session=session,
                student=student,
                defaults={'status': target_status},
            )
        return redirect('attendance_dashboard', session_id=session.id)

    present_students = Presence.objects.filter(
        session=session, status='present'
    ).select_related('student')
    enrolled_students = Student.objects.filter(enrollment__classe=session.classe)
    present_ids = present_students.values_list('student_id', flat=True)
    absent_students = enrolled_students.exclude(id__in=present_ids)
    context = {
        'session': session,
        'present_students': present_students,
        'absent_students': absent_students,
        'present_count': present_students.count(),
        'absent_count': absent_students.count(),
        'total_count': enrolled_students.count(),
        'can_edit': can_edit,
    }
    return render(request, 'attendance_dashboard.html', context)


def attendance_register(request):
    if not request.user.is_authenticated:
        return redirect('signin')

    selected_date_raw = request.GET.get('date', '').strip()
    if selected_date_raw:
        try:
            selected_date = dt_date.fromisoformat(selected_date_raw)
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    if request.user.is_staff:
        classes_qs = Class.objects.all().order_by('name')
    else:
        teacher = Teacher.objects.filter(user=request.user).first()
        classes_qs = Class.objects.filter(teachers=teacher).distinct().order_by('name') if teacher else Class.objects.none()

    selected_class = None
    selected_class_id = request.GET.get('class_id')
    if selected_class_id:
        selected_class = classes_qs.filter(id=selected_class_id).first()
    elif classes_qs.exists():
        selected_class = classes_qs.first()

    rows = []
    session_columns = []
    no_schedule_for_date = False
    if selected_class:
        day_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT'}
        day_label_map = {
            'MON': 'Lundi',
            'TUE': 'Mardi',
            'WED': 'Mercredi',
            'THU': 'Jeudi',
            'FRI': 'Vendredi',
            'SAT': 'Samedi',
        }
        selected_day_code = day_map.get(selected_date.weekday())

        sessions = AttendanceSession.objects.filter(
            classe=selected_class,
            date=selected_date,
        ).select_related('teacher').order_by('start_time')

        # Primary header source: class schedule for the selected day.
        schedule_columns = []
        if selected_day_code:
            selected_day_label = day_label_map.get(selected_day_code)
            schedule_columns = list(
                ClassSchedule.objects.filter(
                    classe=selected_class,
                ).filter(
                    Q(day=selected_day_code) |
                    Q(day__iexact=selected_day_code) |
                    Q(day=selected_day_label) |
                    Q(day__iexact=selected_day_label)
                ).select_related('teacher').order_by('start_time')
            )
            no_schedule_for_date = len(schedule_columns) == 0

        # Keep one concrete session (latest) per teacher for that date.
        latest_session_by_teacher_id = {}
        for session in sessions:
            latest_session_by_teacher_id[session.teacher_id] = session

        if schedule_columns:
            session_columns = [
                {
                    'teacher': schedule.teacher,
                    'matiere': schedule.teacher.matiere,
                    'time_label': f"{schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}",
                    'session': latest_session_by_teacher_id.get(schedule.teacher_id),
                }
                for schedule in schedule_columns
            ]
        else:
            # Fallback: if no schedule row exists for that date, still show teacher headers
            # based on concrete sessions recorded that day.
            session_columns = [
                {
                    'teacher': session.teacher,
                    'matiere': session.teacher.matiere,
                    'time_label': (
                        f"{timezone.localtime(session.start_time).strftime('%H:%M')}-"
                        f"{timezone.localtime(session.end_time).strftime('%H:%M')}"
                        if session.end_time else timezone.localtime(session.start_time).strftime('%H:%M')
                    ),
                    'session': session,
                }
                for session in sessions
            ]

        session_ids = list(sessions.values_list('id', flat=True))

        presence_by_student_session = {}
        if session_ids:
            presences = Presence.objects.filter(
                session_id__in=session_ids
            ).order_by('student_id', 'session_id', '-timestamp')
            for presence in presences:
                key = (presence.student_id, presence.session_id)
                if key not in presence_by_student_session:
                    presence_by_student_session[key] = presence.status

        students = Student.objects.filter(enrollment__classe=selected_class).distinct().order_by('name')
        for student in students:
            rows.append({
                'student': student,
                'default_status': 'absent',
                'statuses': [
                    (
                        presence_by_student_session.get((student.id, col['session'].id), 'absent')
                        if col['session']
                        else 'absent'
                    )
                    for col in session_columns
                ],
            })

    context = {
        'classes': classes_qs,
        'selected_class': selected_class,
        'selected_date': selected_date,
        'rows': rows,
        'session_columns': session_columns,
        'no_schedule_for_date': no_schedule_for_date,
    }
    return render(request, 'attendance_register.html', context)


# ── SCAN WEBHOOK (called by Firebase Cloud Function) ──────────────────────────

@csrf_exempt
def scan_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    uid = data.get('uid', '').strip().upper()
    if not uid:
        return JsonResponse({'error': 'Missing UID'}, status=400)

    # Check teacher card
    teacher = Teacher.objects.filter(uid=uid).first()
    if teacher:
        active_session = AttendanceSession.objects.filter(teacher=teacher, status='OPEN').first()

        if active_session:
            active_session.status = 'CLOSED'
            active_session.end_time = timezone.now()
            active_session.save()
            _mark_absent_students(active_session)
            firebase_utils.update_active_session(None)
            return JsonResponse({'action': 'session_closed', 'session_id': active_session.id})

        now = timezone.localtime()
        schedule = _resolve_teacher_schedule(teacher, now)
        if not schedule:
            return JsonResponse({'error': 'Teacher has no class assigned'}, status=400)

        session = AttendanceSession.objects.create(
            teacher=teacher,
            classe=schedule.classe,
            start_time=timezone.now(),
            status='OPEN',
        )
        firebase_utils.update_active_session(session)
        return JsonResponse({'action': 'session_opened', 'session_id': session.id})

    # Check student card
    student = Student.objects.filter(uid=uid).first()
    if student:
        active_session = AttendanceSession.objects.filter(status='OPEN').first()
        if not active_session:
            return JsonResponse({'error': 'No active session'}, status=400)

        if not Enrollment.objects.filter(student=student, classe=active_session.classe).exists():
            return JsonResponse({'error': 'Student not enrolled in session class'}, status=400)

        _, created = Presence.objects.get_or_create(
            session=active_session,
            student=student,
            defaults={'status': 'present'},
        )
        if not created:
            return JsonResponse({'status': 'already recorded', 'student': student.name})

        return JsonResponse({'action': 'presence_recorded', 'student': student.name})

    return JsonResponse({'status': 'unregistered', 'uid': uid}, status=404)
