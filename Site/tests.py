from django.test import TestCase
import pytz
import datetime
from datetime import timedelta
from Site.models import Person, Manager, ManagerRole, Company, CompanyParticipant, \
        ShareClass, Transfer
from django.test import Client
from django.contrib.auth.models import User
import unittest
from django.conf import settings
import datetime

class SimpleTest(TestCase):
    def setUp(self):
        now = datetime.datetime.now(tz=None)
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
        response = self.client.post("/createPerson/", {"Name": "Sarah",
            "Address": "12 Skylight Ave"})
        response = self.client.post("/companies/create/", {"Name": "Joes Construction",
            "date": "2023-01-01", "time": "00:00:00", "Address": "123 Street"})
        response = self.client.post("/companies/create/", {"Name": "Bobs General Store",
            "date": "2023-01-01", "time": "00:00:00", "Address": "123 Street"})
        response = self.client.post("/companies/create/", {"Name": "Fishmart",
            "date": "2023-01-01", "time": "00:00:00", "Address": "123 Street"})
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
    def construct_authorize(self, params):
        response = self.client.post("/companies/" + \
                str(Company.objects.get(Name=params["company"]).pk) + \
                "/issue/", {"Ammount": params["ammount"], "date": params["date"],
                    "time": params["time"], 
                    "ShareClass": ShareClass.objects.get(Name=params["shareClass"]).pk,
                    "parValue": params["parValue"]})
        return response

    def construct_register(self, company):
        company = Company.objects.get(Name=company)
        response = self.client.get("/companies/"+str(company.pk)+"/registers/?role=ShareHolder")
        return response

    def construct_transfer(self, params):
        _context = dict()
        _from = params["from"]
        if _from["type"] == "person":
            fromPerson = Person.objects.get(Name=_from["name"])
            _context["fromPerson"] = fromPerson.pk
        elif _from["type"] == "company":
            fromCompany = Company.objects.get(Name=_from["name"])
            _context["fromCompany"] = fromCompany.pk

        _to = params["to"]
        if _to["type"] == "person":
            toPerson = Person.objects.get(Name=_to["name"])
            _context["toPerson"] = toPerson.pk
        elif _to["type"] == "company":
            toCompany = Company.objects.get(Name=_to["name"])
            _context["toCompany"] = toCompany.pk

        company = Company.objects.get(Name=params["company"])
        shareClass = ShareClass.objects.get(Name=params["shareClass"])
        _context["shareClass"] = shareClass.pk
        _context["ammount"] = params["ammount"]
        _context["date"] = params["date"]
        _context["time"] = params["time"]
        _context["price"] = params["price"]

        response = self.client.post("/companies/" + str(company.pk) + \
                "/enterTransfer/", _context)

        return response
    def testSetup(self):
        self.construct_people_company_links()
        self.assertEqual(1,1)

    def test_registers(self):
        pass
        self.construct_people_company_links()
        params = {"company": "Joes Construction", "ammount": 1000, 
                "date": "2023-01-01", "time": "00:00:00", "shareClass": "Class A Preferred",
                "parValue": 1}
        response = self.construct_authorize(params)
        self.assertEqual(response.context["alert"], "Shares authorized")

        params = {"company": "Bobs General Store", "ammount": 1000, 
                "date": "2023-01-01", "time": "00:00:00", "shareClass": "Class A Preferred",
                "parValue": 1}
        response = self.construct_authorize(params)
        self.assertEqual(response.context["alert"], "Shares authorized")

        params = {"company": "Bobs General Store", "ammount": 1000, 
                "date": "2023-01-01", "time": "00:00:00", "shareClass": "Class B Preferred",
                "parValue": 1}
        response = self.construct_authorize(params)
        self.assertEqual(response.context["alert"], "Shares authorized")

        params = {"from": {"type": "company", "name": "Bobs General Store"}, 
            "to": {"type": "person", "name": "Sarah"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "100", "date": "2023-01-01", "time": "01:00:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        params = {"from": {"type": "company", "name": "Bobs General Store"}, 
            "to": {"type": "person", "name": "Sarah"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "200", "date": "2023-01-01", "time": "01:01:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        #Sarah now at 300 class A

        params = {"from": {"type": "person", "name": "Sarah"}, 
            "to": {"type": "person", "name": "John"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "50", "date": "2023-01-01", "time": "01:02:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        #Sarah now at 250, John at 50

        params = {"from": {"type": "person", "name": "John"}, 
            "to": {"type": "person", "name": "Sarah"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "100", "date": "2023-01-01", "time": "01:03:01",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before, len_after)

        #Sarah now at 250, John at 50

        #Test sarah
        response = self.construct_register("Bobs General Store")
        entries = response.context["entityShareClass"]
        shareClass = ShareClass.objects.get(Name="Class A Preferred")
        person = Person.objects.get(Name="Sarah")
        for key in list(entries.keys()):
            if shareClass in key and person in key:
                self.assertEqual(entries[key][0], 250)
                break

        #Test John
        person = Person.objects.get(Name="John")
        for key in list(entries.keys()):
            if shareClass in key and person in key:
                self.assertEqual(entries[key][0], 50)
                break

        params = {"from": {"type": "person", "name": "Sarah"}, 
            "to": {"type": "company", "name": "Bobs General Store"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "50", "date": "2023-01-01", "time": "01:04:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        #Sarah now at 200, John at 50

        #Test sarah
        response = self.construct_register("Bobs General Store")
        entries = response.context["entityShareClass"]
        shareClass = ShareClass.objects.get(Name="Class A Preferred")
        person = Person.objects.get(Name="Sarah")
        for key in list(entries.keys()):
            if shareClass in key and person in key:
                self.assertEqual(entries[key][0], 200)
                break


        
    def test_enough_company(self):
        pass
        self.construct_people_company_links()
        params = {"company": "Joes Construction", "ammount": 1000, 
                "date": "2023-01-01", "time": "00:00:00", "shareClass": "Class A Preferred",
                "parValue": 1}
        response = self.construct_authorize(params)
        self.assertEqual(response.context["alert"], "Shares authorized")

        params = {"company": "Bobs General Store", "ammount": 1000, 
                "date": "2023-01-01", "time": "00:00:00", "shareClass": "Class A Preferred",
                "parValue": 1}
        response = self.construct_authorize(params)
        self.assertEqual(response.context["alert"], "Shares authorized")

        params = {"company": "Bobs General Store", "ammount": 1000, 
                "date": "2023-01-01", "time": "00:00:00", "shareClass": "Class B Preferred",
                "parValue": 1}
        response = self.construct_authorize(params)
        self.assertEqual(response.context["alert"], "Shares authorized")


        #bobs gen = 800 auth = 1000 sarah = 800
        params = {"from": {"type": "company", "name": "Bobs General Store"}, 
            "to": {"type": "person", "name": "Sarah"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "800", "date": "2023-01-01", "time": "01:00:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        #bobs gen = 0 auth = 1000 joes con = 200 sarah =800
        params = {"from": {"type": "company", "name": "Bobs General Store"}, 
            "to": {"type": "company", "name": "Joes Construction"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "200", "date": "2023-01-01", "time": "01:01:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        #FAIL bobs gen = 0 auth = 1000 joes con = 200 sarah =800
        params = {"from": {"type": "company", "name": "Joes Construction"}, 
            "to": {"type": "person", "name": "Sarah"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "201", "date": "2023-01-01", "time": "01:01:01",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before, len_after)

        # FAIL bobs gen = 0 auth = 1000 joes con = 200 sarah = 800
        params = {"from": {"type": "company", "name": "Joes Construction"}, 
            "to": {"type": "company", "name": "Bobs General Store"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "200", "date": "2023-01-01", "time": "01:00:05",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before, len_after)
        
        
        #FAIL bobs gen = 0 auth = 1000 joes con = 200 sarah = 800
        params = {"from": {"type": "company", "name": "Bobs General Store"}, 
            "to": {"type": "person", "name": "Tim"},
            "shareClass": "Class A Preferred", "company": "Bobs General Store",
            "ammount": "1", "date": "2023-01-01", "time": "01:02:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before, len_after)

        params = {"from": {"type": "company", "name": "Joes Construction"}, 
            "to": {"type": "person", "name": "Tim"},
            "shareClass": "Class A Preferred", "company": "Joes Construction",
            "ammount": "600", "date": "2023-01-01", "time": "01:01:05",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        params = {"from": {"type": "person", "name": "Tim"}, 
            "to": {"type": "company", "name": "Joes Construction"},
            "shareClass": "Class A Preferred", "company": "Joes Construction",
            "ammount": "100", "date": "2023-01-01", "time": "01:01:09",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        params = {"from": {"type": "company", "name": "Joes Construction"}, 
            "to": {"type": "person", "name": "Tim"},
            "shareClass": "Class A Preferred", "company": "Joes Construction",
            "ammount": "400", "date": "2023-01-01", "time": "01:02:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        params = {"from": {"type": "company", "name": "Joes Construction"}, 
            "to": {"type": "person", "name": "Tim"},
            "shareClass": "Class A Preferred", "company": "Joes Construction",
            "ammount": "1", "date": "2023-01-01", "time": "01:03:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before, len_after)

        params = {"from": {"type": "person", "name": "Tim"}, 
            "to": {"type": "company", "name": "Joes Construction"},
            "shareClass": "Class A Preferred", "company": "Joes Construction",
            "ammount": "900", "date": "2023-01-01", "time": "01:00:30",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before, len_after)

        params = {"from": {"type": "person", "name": "Tim"}, 
            "to": {"type": "company", "name": "Joes Construction"},
            "shareClass": "Class A Preferred", "company": "Joes Construction",
            "ammount": "900", "date": "2023-01-01", "time": "01:04:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before + 1, len_after)

        params = {"from": {"type": "company", "name": "Joes Construction"}, 
            "to": {"type": "person", "name": "Tim"},
            "shareClass": "Class A Preferred", "company": "Joes Construction",
            "ammount": "1", "date": "2023-01-01", "time": "01:05:00",
            "price": "1",}
        len_before = len(Transfer.objects.all())
        response = self.construct_transfer(params)
        len_after = len(Transfer.objects.all())
        self.assertEqual(len_before, len_after)




    def test_create_manager(self):
        pass
        response = self.client.post("/managerRole/", {"title": "CEO"})
        created = response.context["alert"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(created, "Management Role Created")
        l = len(ManagerRole.objects.all())
        self.assertEqual(l, 1)

    def test_manager_delete(self):
        pass
        response = self.client.post("/managerRole/", {"title": "CEO"})
        role = ManagerRole.objects.all()[0]
        pk = role.pk
        response = self.client.get("/managerRole/?delete="+str(pk))
        deleted = response.context["alert"]
        self.assertEqual(deleted, "Management Role Deleted")
