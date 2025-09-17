
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import AddDoctorForm, ContactForm, LoginForm, RegisterForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import JsonResponse
from .models import Doctor, MeetingHistory
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta
import json
from django.contrib.auth.forms import AuthenticationForm
from reportlab.pdfgen import canvas 
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from collections import defaultdict
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from io import BytesIO
from django.utils.timezone import now
from django.urls import reverse
import calendar
import random
from django.views.decorators.cache import never_cache



# Create your views here.

bold_path = os.path.join(settings.BASE_DIR, "remainderapp", "static", "fonts", "LibertinusSerif-Bold.ttf")
regular_path = os.path.join(settings.BASE_DIR, "remainderapp", "static", "fonts", "LibertinusSerif-Regular.ttf")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            user_email = request.user.email if request.user.is_authenticated else "Anonymous"

            full_message = f"From: {user_email}\n\nMessage:\n{message}"

            # Send mail to you (admin)
            try:
                send_mail(
                    subject,
                    full_message,
                    settings.EMAIL_HOST_USER,   # from your configured email
                    ["kvarun162006@gmail.com"], # <-- replace with your email
                    fail_silently=False,
                )

                messages.success(request, "Your message has been sent. We'll get back to you soon.")
            except Exception as e:
                messages.error(request, f"❌ Error sending message: {e}")

            return redirect("remainderapp:dashboard")  # adjust to your dashboard URL name
    else:
        form = ContactForm()

    return render(request, "remainderapp/contact.html", {"form": form})



def index(request):
    return render(request, 'remainderapp/base.html')

def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    

    form = RegisterForm()
    if request.method =='POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, "Account Created Successfully!")
            return redirect("remainderapp:login")
    return render(request, 'remainderapp/register.html',{'form':form})

def login(request):
     

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request,username=username, password=password)
            if user is not None:
                auth_login(request, user)

                messages.success(request, f"Welcome back {user.username}!")
                return redirect("remainderapp:dashboard")
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, "remainderapp/login.html", {"form": form})



@login_required
@never_cache
def add_doctors(request):
    if request.method == "POST":
        form = AddDoctorForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            
            try:
                # Read file with pandas
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Check required columns
                required_cols = ['Name', 'LastMet']
                if not all(col in df.columns for col in required_cols):
                    messages.error(request, "File must have 'Name' and 'LastMet' columns.")
                    return redirect('remainderapp:add_doctors')
                
                # Iterate and save
                for _, row in df.iterrows():
                    Doctor.objects.create(
                        name=row['Name'],
                        lastMet=row['LastMet'],
                        location=row.get('Location', ''),
                        user = request.user
                    )
                messages.success(request, f"{len(df)} doctors added successfully!")
            except Exception as e:
                messages.error(request, f"Error processing file: {e}")

            return redirect('remainderapp:add_doctors')
    else:
        form = AddDoctorForm()

    return render(request, 'remainderapp/add_doctors.html', {'form': form})


@login_required
@never_cache
def dashboard(request):
    return render (request, 'remainderapp/dashboard.html')


@csrf_exempt

@never_cache
def doctor_list_api(request):
    if request.method == "GET":
        doctors = Doctor.objects.filter(user=request.user)
        data = []
        for doc in doctors:
            data.append({
                "id": doc.id,
                "name": doc.name,
                "location": doc.location,
                "lastMet": doc.lastMet.strftime("%d-%m-%Y") if doc.lastMet else None
            })
        return JsonResponse(data, safe=False)

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        name = data.get("name")
        last_met = data.get("lastMet")
        location = data.get("location", "")

        if not name:
            return JsonResponse({"error": "Name is required"}, status=400)

        # Convert lastMet safely
        date_obj = None
        if last_met:
            try:
                date_obj = datetime.strptime(last_met, "%d-%m-%Y").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use DD-MM-YYYY."}, status=400)

        doc = Doctor.objects.create(
            user=request.user,
            name=name,
            lastMet=date_obj,
            location=location
        )

        return JsonResponse({
            "id": doc.id,
            "name": doc.name,
            "lastMet": doc.lastMet.strftime("%d-%m-%Y") if doc.lastMet else None,
            "location": doc.location
        })



@never_cache
def available_months(request):
    doctors = Doctor.objects.exclude(lastMet__isnull=True)

    month_set = set()
    for doc in doctors:
        if doc.lastMet:  # already a date object
            month_set.add((doc.lastMet.year, doc.lastMet.month))

    month_list = []
    for year, month in sorted(month_set, reverse=True):
        month_name = calendar.month_name[month]
        month_list.append({
            "year": year,
            "month": month,
            "label": f"{month_name} {year}",
            # ✅ match your React `handleDownloadPdf` URL
            "download_url": f"/doctors/pdf/{year}/{month}/"
        })

    return JsonResponse({"months": month_list})



@never_cache
def doctor_list(request):
    doctors = Doctor.objects.filter(user=request.user)
    return render (request, 'remainderapp/doctor_list.html',{'doctors':doctors})

@csrf_exempt
@login_required
@never_cache
def doctor_delete_api(request, id):
    if request.method == "DELETE":
        try:
            doctor = Doctor.objects.get(id=id, user= request.user)
            doctor.delete()
            return JsonResponse({"success": True, "id": id})
        except Doctor.DoesNotExist:
            return JsonResponse({"error": "Doctor not found"}, status=404)
    return JsonResponse({"error": "Invalid method"}, status=400)

@csrf_exempt
@login_required
@never_cache
def doctor_update_api(request, id):
    if request.method != "PUT":
        return JsonResponse({"error": "Invalid method"}, status=400)

    try:
        doctor = Doctor.objects.get(id=id, user=request.user)
    except Doctor.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    last_met = data.get("lastMet")
    if not last_met or last_met.strip() == "":
        return JsonResponse({"error": "lastMet cannot be empty"}, status=400)

    try:
        new_date = datetime.strptime(last_met, "%d-%m-%Y").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format. Use DD-MM-YYYY."}, status=400)

    # Optional: prevent decreasing the date
    if doctor.lastMet and new_date < doctor.lastMet:
        return JsonResponse({
            "error": f"Date must be after last updated date ({doctor.lastMet.strftime('%d-%m-%Y')})"
        }, status=400)

    doctor.lastMet = new_date
    doctor.save()

    # Avoid duplicate MeetingHistory
    if not doctor.meetings.filter(meeting_date=new_date).exists():
        MeetingHistory.objects.create(doctor=doctor, meeting_date=new_date)

    return JsonResponse({
        "success": True,
        "id": doctor.id,
        "lastMet": doctor.lastMet.strftime("%d-%m-%Y")
    })


@never_cache
def logout(request):
    auth_logout(request)
    return redirect ("remainderapp:login")

@login_required
@never_cache
def download_meeting_history(request, doctor_id):
    try:
        doctor = Doctor.objects.get(id=doctor_id, user=request.user)
        meetings = doctor.meetings.all().order_by("meeting_date")  # chronological

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{doctor.name}_monthly_history.pdf"'

        doc = SimpleDocTemplate(response, pagesize=A4)
        story = []

        # Register the fonts
        pdfmetrics.registerFont(TTFont('Libertinus-Bold', bold_path))
        pdfmetrics.registerFont(TTFont('Libertinus-Regular', regular_path))

        # Initialize styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='RightSmall', fontName='Libertinus-Regular', fontSize=10,
            alignment=TA_RIGHT, textColor=colors.HexColor('#6c6c6c')
        ))  
        styles.add(ParagraphStyle(
            name='TitlePremium', fontName='Libertinus-Bold', fontSize=22,
            alignment=TA_CENTER, textColor=colors.HexColor('#2c3e50')
        ))
        styles.add(ParagraphStyle(
            name='MonthHeader', fontName='Libertinus-Bold', fontSize=14,
            alignment=TA_CENTER, textColor=colors.HexColor('#34495e')
        ))

        # User info and download date
        user = request.user.username
        today_str = datetime.now().strftime("%d %b %Y, %H:%M")
        story.append(Paragraph(f"User: {user}", styles['RightSmall']))
        story.append(Paragraph(f"Downloaded: {today_str}", styles['RightSmall']))
        story.append(Spacer(1, 10))

        # Title
        story.append(Paragraph(f"Meeting History for Dr. {doctor.name}", styles['TitlePremium']))
        story.append(Spacer(1, 20))

        if meetings.exists():
            # Group meetings by month
            monthly_meetings = defaultdict(list)
            for m in meetings:
                month_key = m.meeting_date.strftime("%B %Y")  # e.g., "August 2025"
                monthly_meetings[month_key].append(m)

            for month, month_meetings in monthly_meetings.items():
                story.append(Paragraph(f"{month} - Total Visits: {len(month_meetings)}", styles['MonthHeader']))
                story.append(Spacer(1, 10))

                # Table for this month
                data = [["S.No", "Meeting Date"]]
                for idx, m in enumerate(month_meetings, start=1):
                    data.append([str(idx), m.meeting_date.strftime("%d-%m-%Y")])

                table = Table(data, colWidths=[50, 150])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eaf2f8')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#2c3e50')),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Libertinus-Bold'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 12),
                    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f5f7fa')),
                    ('TEXTCOLOR', (0,1), (-1,-1), colors.HexColor('#34495e')),
                    ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d1d5db')),
                ]))
                story.append(table)
                story.append(Spacer(1, 20))
        else:
            story.append(Paragraph("No meetings recorded yet.", styles['RightSmall']))

        doc.build(story)
        return response

    except Doctor.DoesNotExist:
        return HttpResponse("Doctor not found", status=404)

@login_required
@never_cache
def download_all_doctors_pdf(request):
    return _generate_doctors_pdf(request)


@login_required
@never_cache
def download_monthly_doctors_pdf(request, year, month):
    return _generate_doctors_pdf(request, year, month)

@login_required
@never_cache
@login_required
@never_cache
def _generate_doctors_pdf(request, year=None, month=None):
    user = request.user.username
    today_str = datetime.now().strftime("%d %b %Y")

    # Response + filename
    response = HttpResponse(content_type='application/pdf')
    if year and month:
        month_name = datetime(int(year), int(month), 1).strftime("%B")
        filename = f"doctors_{month_name}_{year}.pdf"
    else:
        filename = "doctors.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # PDF Document
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    # Fonts
    pdfmetrics.registerFont(TTFont('Libertinus-Bold', bold_path))
    pdfmetrics.registerFont(TTFont('Libertinus-Regular', regular_path))

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='RightSmall', fontName='Libertinus-Regular',
        fontSize=10, alignment=TA_RIGHT, textColor=colors.HexColor('#6c6c6c')
    ))
    styles.add(ParagraphStyle(
        name='TitlePremium', fontName='Libertinus-Bold',
        fontSize=22, alignment=TA_CENTER, textColor=colors.HexColor('#2c3e50')
    ))

    # Header info
    elements.append(Paragraph(f"User: {user}", styles['RightSmall']))
    elements.append(Paragraph(f"Downloaded: {today_str}", styles['RightSmall']))
    elements.append(Spacer(1, 10))

    # Title
    title = "Doctors List"
    if year and month:
        title = f"Doctors Report - {datetime(int(year), int(month), 1).strftime('%B %Y')}"
    elements.append(Paragraph(title, styles['TitlePremium']))
    elements.append(Spacer(1, 20))

    # Fetch doctors for this user
    doctors = Doctor.objects.filter(user=request.user)
    if year and month:
        # For monthly report, only include doctors with meetings in that month
        doctors = [doc for doc in doctors if doc.meetings.filter(
            meeting_date__year=year,
            meeting_date__month=month
        ).exists()]

    # Table header
    table_header = ["S.No", "Doctor Name", "Location"]
    table_header.append(f"Meeting Dates ({datetime(int(year), int(month), 1).strftime('%b %Y')})" 
                        if year and month else "Meeting Dates")
    data = [table_header]

    # Table rows
    for idx, doc_item in enumerate(doctors, start=1):
        # Get meetings for the month or all meetings
        if year and month:
            meetings = doc_item.meetings.filter(
                meeting_date__year=year,
                meeting_date__month=month
            ).values_list("meeting_date", flat=True)
        else:
            meetings = doc_item.meetings.all().values_list("meeting_date", flat=True)

        # Format dates
        days = sorted([d.strftime("%d-%m-%Y") for d in meetings])
        data.append([
            str(idx),
            f"Dr. {doc_item.name}",
            doc_item.location,
            ", ".join(days) if days else "-"
        ])

    # Create table
    table = Table(data, colWidths=[50, 150, 150, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf2f8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Libertinus-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f7fa')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#34495e')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
    ]))
    elements.append(table)

    doc.build(elements)
    return response



def send_doctors_pdf_to_users(request):
    try:
        # Determine user
        user = request.user if request.user.is_authenticated else None
        doctors = Doctor.objects.filter(user=user) if user else Doctor.objects.none()
        recipient_email = user.email if user and user.email else "kvarun162006@gmail.com"

        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='TitlePremium', fontSize=20, alignment=TA_CENTER, textColor=colors.HexColor('#2c3e50')))
        styles.add(ParagraphStyle(name='SubInfo', fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor('#7f8c8d')))

        # Title + timestamp
        elements.append(Paragraph("Doctors List", styles['TitlePremium']))
        elements.append(Spacer(1, 12))
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        elements.append(Paragraph(f"Generated on: {now_str}", styles['SubInfo']))
        elements.append(Spacer(1, 20))

        # Table headers
        data = [["S.No", "Doctor Name", "Location", "Last Met", "Days Passed"]]
        today = datetime.today().date()

        # Table rows
        for idx, doc_item in enumerate(doctors, start=1):
            days_passed = (today - doc_item.lastMet).days
            lastmet_str = doc_item.lastMet.strftime("%d-%m-%Y")
            data.append([
                str(idx),
                f"Dr. {doc_item.name}",
                doc_item.location,
                lastmet_str,
                str(days_passed)
            ])

        # Table formatting
        table = Table(data, colWidths=[50, 150, 120, 100, 100])
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eaf2f8')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#2c3e50')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d1d5db')),
        ])

        # Highlight overdue doctors
        for i, doc_item in enumerate(doctors, start=1):
            if (today - doc_item.lastMet).days > 10:
                table_style.add('BACKGROUND', (0,i), (-1,i), colors.HexColor('#f8d7da'))

        table.setStyle(table_style)
        elements.append(table)

        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        # Send email
        email = EmailMessage(
            subject="Doctors List - Missed Calls Highlighted",
            body="Here is the list attached with missed calls for more than 10 days.",
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient_email],
        )
        email.attach("Doctors_List.pdf", pdf, "application/pdf")

        try:
            email.send(fail_silently=False)
        except Exception as e:
            print("Email sending failed:", e)
            return JsonResponse({"success": False, "message": f"Email sending failed: {e}"}, status=500)

        return JsonResponse({"success": True, "message": f"Email sent successfully to {recipient_email}!"})

    except Exception as e:
        print("Error generating PDF:", e)
        return JsonResponse({"success": False, "message": f"Error generating PDF: {e}"}, status=500)