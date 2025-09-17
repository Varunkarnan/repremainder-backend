from django.urls import path
from . import views

app_name= 'remainderapp'

urlpatterns = [
    
    path("",views.register,name="register"),
    path("login/",views.login,name="login"),
    path("contact/", views.contact, name="contact"),
    path("dashboard/",views.dashboard,name="dashboard"),
    path("add_doctors/",views.add_doctors,name="add_doctors"),
    path("api/doctors/",views.doctor_list_api,name="doctor_list_api"),
    path("doctors/",views.doctor_list,name="doctor_list"),
    path("react-doctors/",views.doctor_list, name="react_doctors"),
    path("api/doctors/<int:id>/delete/", views.doctor_delete_api, name="doctor_delete_api"),
    path("api/doctors/<int:id>/update/", views.doctor_update_api, name="doctor_update_api"),
    path("logout/", views.logout,name="logout"),
    path("api/doctors/<int:doctor_id>/download-history/", views.download_meeting_history, name="download_meeting_history"),
    path('api/download/all-doctors/pdf/', views.download_all_doctors_pdf, name='download_pdf'),
    path('send-doctors-email/', views.send_doctors_pdf_to_users, name='send_doctors_pdf'),
    path("doctors/pdf/<int:year>/<int:month>/", views.download_monthly_doctors_pdf, name="download_doctors_pdf"),
    path("doctors/months/", views.available_months, name="available_months"),


]
