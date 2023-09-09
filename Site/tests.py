from django.test import TestCase
import pytz
import datetime
from datetime import timedelta
from Site.models import Person, Manager, ManagerRole, Company, CompanyParticipant, ShareClass
from django.test import Client
from django.contrib.auth.models import User
import unittest

class SimpleTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="aaron1", password="password1")
        self.client.login(username="aaron1", password="password1")


    def construct_people_company_links(self):
        response = self.client.post("/createPerson/", {"Name": "John",
            "Address": "123 Main street"})
        response = self.client.post("/createPerson/", {"Name": "Tim",
            "Address": "32 Rocky Ave"})
        response = self.client.post("/createPerson/", {"Name": "Amy",
            "Address": "55 South Street"})
        response = self.client.post("/createPerson/", {"Name": "Abby",
            "Address": "12 Skylight Ave"})
        response = self.client.post("/companies/create/", {"Name": "Joes Construction"})
        response = self.client.post("/companies/create/", {"Name": "Bobs General Store"})
        response = self.client.post("/companies/create/", {"Name": "Fishmart"})
        response = self.client.post("/shareClass/", {"name": "Class A Preferred"})
        response = self.client.post("/shareClass/", {"name": "Class B Preferred"})
        response = self.client.post("/shareClass/", {"name": "Class C Preferred"})
        person_ids = [x.id for x in Person.objects.all()]
        company_ids = [x.id for x in Company.objects.all()]
        for p_id in person_ids:
            for c_id in company_ids:
                response = self.client.get("/link/" + str(p_id) + "/?company_id=" + str(c_id) \
                        + "&type=person")
        for c_id in company_ids:
            for c_id2 in company_ids:
                response = self.client.get("/link/" + str(c_id) + "/?company_id=" + str(c_id2) \
                        + "&type=company")
        date = "2023-02-01"
        time = "12:0:0"
        ammount = 1000
        class_a_id = ShareClass.objects.all()[0].pk
        joes_construction_id = Company.objects.all()[0].pk
        parValue = 1.5
        response = self.client.post("/companies/" + str(joes_construction_id) + \
                "/issue/", {"Ammount" : ammount, "date" : date, "time" : time,
                    "ShareClass": class_a_id})
        print(response.context["alert"])


    def test_t(self):
        self.construct_people_company_links()
        joes_construction = Company.objects.get(Name="Joes Construction")
        tim = Person.objects.get(Name = "Tim")
        abby = Person.objects.get(Name = "Abby")
        class_a = ShareClass.objects.get(Name = "Class A Preferred")
        date = "2023-02-01"
        time = "13:0:0"
        params = {"fromCompany" : joes_construction.pk, "toPerson" : tim.pk,
                "date" : date, "time" : time, "shareClass" : class_a.pk,
                "ammount" : 250, "price" : 10}
        response = self.client.post("/companies/" + str(joes_construction.id) + \
                "/enterTransfer/", params)
        self.assertEqual(response.context["alert"], "Transfer Saved")

        date = "2023-02-01"
        time = "11:0:0"
        params = {"fromCompany" : joes_construction.pk, "toPerson" : tim.pk,
                "date" : date, "time" : time, "shareClass" : class_a.pk,
                "ammount" : 250, "price" : 10}
        response = self.client.post("/companies/" + str(joes_construction.id) + \
                "/enterTransfer/", params)
        self.assertEqual(response.context["alert"], "Not enough shares!")

        #Joes cons = 1000 auth, 250 issued, Tim = 250

        date = "2023-02-01"
        time = "14:0:0"
        params = {"fromPerson" : tim.pk, "toCompany" : joes_construction.pk,
                "date" : date, "time" : time, "shareClass" : class_a.pk,
                "ammount" : 250, "price" : 10}
        response = self.client.post("/companies/" + str(joes_construction.id) + \
                "/enterTransfer/", params)
        self.assertEqual(response.context["alert"], "Transfer Saved")

        #joes cons = 750 auth, 0 issued, tim = 0

        date = "2023-02-01"
        time = "15:0:0"
        params = {"fromCompany" : joes_construction.pk, "toPerson" : tim.pk,
                "date" : date, "time" : time, "shareClass" : class_a.pk,
                "ammount" : 750, "price" : 10}
        response = self.client.post("/companies/" + str(joes_construction.id) + \
                "/enterTransfer/", params)
        self.assertEqual(response.context["alert"], "Transfer Saved")
        
        #joes cons = 750 auth, 750 issued, tim = 750

        date = "2023-02-01"
        time = "16:0:0"
        params = {"fromCompany" : joes_construction.pk, "toPerson" : tim.pk,
                "date" : date, "time" : time, "shareClass" : class_a.pk,
                "ammount" : 50, "price" : 10}
        response = self.client.post("/companies/" + str(joes_construction.id) + \
                "/enterTransfer/", params)
        self.assertEqual(response.context["alert"], "Not enough shares!")

        #joes cons = 750 auth, 750 issued, tim = 750

        date = "2023-01-01"
        time = "16:0:0"
        params = {"fromCompany" : joes_construction.pk, "toPerson" : tim.pk,
                "date" : date, "time" : time, "shareClass" : class_a.pk,
                "ammount" : 50, "price" : 10}
        response = self.client.post("/companies/" + str(joes_construction.id) + \
                "/enterTransfer/", params)
        self.assertEqual(response.context["alert"], "Not enough shares!")



    def test_create_manager(self):
        response = self.client.post("/managerRole/", {"title": "CEO"})
        created = response.context["alert"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(created, "Management Role Created")
        l = len(ManagerRole.objects.all())
        self.assertEqual(l, 1)

    def test_manager_delete(self):
        response = self.client.post("/managerRole/", {"title": "CEO"})
        role = ManagerRole.objects.all()[0]
        pk = role.pk
        response = self.client.get("/managerRole/?delete="+str(pk))
        deleted = response.context["alert"]
        self.assertEqual(deleted, "Management Role Deleted")
