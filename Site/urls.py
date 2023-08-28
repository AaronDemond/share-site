from django.urls import path

from . import views

urlpatterns = [
        path("", views.index, kwargs={'a':1}, name="index"),
        path("companies/", views.companies, name="companies"),
        path('companies/<int:company_id>/issue/', views.issue_shares, name="issue"),
        path('companies/<int:company_id>/shareholdersRegister/', views.shareholders_register, name="shareholders_register"),
        path('companies/<int:company_id>/shareholdersLedger/', views.shareholders_ledger, name="shareholders_ledger"),
        path('companies/<int:company_id>/enterTransfer/', views.enter_transfer, name="enter_transfer"),
        path('companies/<int:company_id>/changeManagement/', views.management, name="management"),
        path('companies/<int:company_id>/transfers/', views.transfers, name="transfers"),
        path('companies/<int:company_id>/registers/', views.registers, name="registers"),
        path('companies/<int:company_id>/certificates/<int:transfer_id>/', views.transfers, name="certificate"),
        path('companies/create/', views.create_company, name="create_company"),
        path('createPerson/', views.create_person, name="create_person"),

        path("entities/", views.people, name="entities"),
        path("certificates/", views.share_certificate, name="share_certificate"),
        path("certificates/<int:company_id>/", views.share_certificate, name="share_certificate_single"),
        path("shareClass/", views.share_class, name="share_class"),
        path("managerRole/", views.manager_role, name="manager_role"),
        path('link/<int:_id>/', views.link, name="link"),
]
