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
        path('companies/create/', views.create_company, name="create_company"),

        path("entities/", views.people, name="entities"),
        path('link/<int:_id>/', views.link, name="link"),
        path('link/<int:_id>/', views.link, name="link"),
]
