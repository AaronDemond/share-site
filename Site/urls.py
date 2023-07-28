from django.urls import path

from . import views

urlpatterns = [
        path("", views.index, kwargs={'a':1}, name="index"),
        path("companies/", views.companies, name="companies"),
        path('companies/<int:company_id>/issue/', views.issue_shares, name="issue"),
        path('companies/<int:company_id>/shareholdersRegister/', views.shareholders_register, name="shareholders_register"),
        path('companies/<int:company_id>/shareholdersLedger/', views.shareholders_ledger, name="shareholders_ledger"),
        path('companies/<int:company_id>/shareholdersLedger/<int:person_id>/<int:share_class_id>/', views.shareholders_ledger, name="shareholders_ledger"),
        path('companies/<int:company_id>/enterTransfer/', views.enter_transfer, name="enter_transfer"),
        path('companies/create/', views.create_company, name="create_company"),
        path('ajax/fromCompany/', views.fromCompany, name="fromCompany"),
        path('ajax/personSearch/', views.personSearch, name="personSearch"),
        path('ajax/companies/', views.companiesAjax, name="companiesAjax"),

        path("people/", views.people, name="people"),
        path('people/<int:person_id>/enterTransfer/', views.enter_transfer_person, name="enter_transfer"),
]
