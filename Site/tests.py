from django.test import TestCase
from Site.models import Person, Manager
from django.test import Client

class SimpleTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.login(username="aaron1", password="password")

    def test_create_manager(self):
        response = self.client.post("/managerRole/", {"title": "CEO"})
        self.assertEqual(response.status_code, 200)
