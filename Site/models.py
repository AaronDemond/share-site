from django.db import models
import pytz
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
import datetime


class Person(models.Model):
    Name = models.CharField(max_length=500)
    Address = models.CharField(max_length=500)
    Modified= models.DateTimeField()

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        modified = datetime.datetime.now()
        #date = pytz.timezone("America/Halifax").localize(modified)
        self.Modified = modified
        return super(Person, self).save(*args, **kwargs)

    def __str__(self):
        return self.Name
    
class Company(models.Model):
    Name = models.CharField(max_length=500)
    Modified= models.DateTimeField()
    IncorporationDate = models.DateTimeField()
    Address = models.CharField(max_length=500)

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        modified = datetime.datetime.now()
        #date = pytz.timezone("America/Halifax").localize(modified)
        self.Modified = modified
        if self.Name == "":
            raise Exception("Can't be a blank name")
        else:
            super(Company, self).save(*args, **kwargs)

    def __str__(self):
        return self.Name
class ManagerRole(models.Model):
    Title = models.CharField(max_length=500, unique = True)

    def __str__(self):
        return self.Title
class Manager(models.Model):

    titles = [
            ("Officer", "Officer"),
            ("President", "President"), 
            ("Secretary", "Secretary"),
            ("VP", "VP"),
            ("Director", "Director"),
            ("Other", "Other")
            ]
    Person = models.ForeignKey(Person, on_delete=models.CASCADE, unique = False,
            related_name = "Manager")
    Title = models.ForeignKey(ManagerRole, on_delete=models.CASCADE, unique = False,
            related_name = "Manager")
    #Title = models.CharField(max_length=200, choices=titles)
    Company = models.ForeignKey(Company, on_delete=models.CASCADE, unique = False,
            related_name = "Manager")
    StartDate= models.DateTimeField()
    EndDate= models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.Person) + " " + str(self.Title) + " at " + str(self.Company)

class ShareClass(models.Model):
    Name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.Name)
    class Meta:
        verbose_name_plural = "ShareClasses"

class AuthorizedShares(models.Model):
    Company = models.ForeignKey(Company, on_delete=models.CASCADE,
            related_name = "AuthorizedShares")
    Ammount = models.FloatField()
    ShareClass = models.ForeignKey(ShareClass, on_delete=models.CASCADE,
            related_name="AuthorizedShares")
    Date = models.DateTimeField()
    Value = models.FloatField(null = True, blank = True)
    Document = models.FileField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if int(self.Ammount) < 0:
            raise Exception("Must be above zero")
        else:
            super(AuthorizedShares, self).save(*args, **kwargs)

    def __str__(self):
        dt = self.Date.strftime("%Y-%m-%d %H:%M:%S")
        return str(self.Ammount) + " of " + str(self.ShareClass) + " for " + str(self.Company) + " on " + dt

    class Meta:
        verbose_name_plural = "AuthorizedShares"

class CompanyParticipant(models.Model):
    CompanyReference = models.ForeignKey(Company, null=True, blank=True, on_delete =models.CASCADE,
            related_name = "Participant")
    LinkedPerson = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE,
            related_name = "LinkedCompany")
    LinkedCompany = models.ForeignKey(Company, null=True, blank=True, on_delete =models.CASCADE,
            related_name = "LinkedCompany")

    def __str__(self):
        if self.LinkedPerson:
            return self.LinkedPerson.Name + " is linked to " + self.CompanyReference.Name
        elif self.LinkedCompany:
            return self.LinkedCompany.Name + " is linked to " + self.CompanyReference.Name

    
class Transfer(models.Model):
    FromCompany = models.ForeignKey(Company, null=True, blank=True, on_delete =models.CASCADE,
            related_name = "FromCompanyTransfer")
    FromPerson = models.ForeignKey(Person, null = True, blank = True, on_delete = models.CASCADE,
            related_name = "FromPersonTransfer")
    ToCompany = models.ForeignKey(Company, null=True, blank=True, on_delete = models.CASCADE,
            related_name = "ToCompanyTransfer")
    ToPerson = models.ForeignKey(Person, null = True, blank = True, on_delete = models.CASCADE,
            related_name = "ToPersonTransfer")
    Company = models.ForeignKey(Company, on_delete = models.CASCADE, related_name = "Transfer")
    Date = models.DateTimeField()
    Ammount = models.FloatField()
    ShareClass = models.ForeignKey(ShareClass, on_delete =models.CASCADE)
    Price = models.FloatField()

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        self.Company.Modified = datetime.datetime.now()
        if self.ToPerson:
            self.ToPerson.Modified = datetime.datetime.now()
            self.ToPerson.save()
        if self.FromPerson:
            self.FromPerson.Modified = datetime.datetime.now()
            self.FromPerson.save()
        if self.ToCompany:
            self.ToCompany.Modified = datetime.datetime.now()
            self.ToCompany.save()
        if self.FromCompany:
            self.FromCompany.Modified = datetime.datetime.now()
            self.FromCompany.save()

        return super(Transfer, self).save(*args, **kwargs)


    def __str__(self):
        _from = self.FromPerson or self.FromCompany
        _to = self.ToPerson or self.ToCompany
        if self.Ammount.is_integer():
            ammount = int(self.Ammount)
        else:
            ammount = self.Ammount
        dt = self.Date.strftime("%Y-%m-%d %H:%M:%S")
        return str(ammount) + " " + str(self.ShareClass) + " shares from " + _from.Name + " to " + _to.Name + " on (" + dt + ")"


class ShareCertificate(models.Model):
    ReferenceCompany = models.ForeignKey(Company, on_delete=models.CASCADE,
            related_name = "ShareCertificate")
    Ammount = models.FloatField()
    ShareClass = models.ForeignKey(ShareClass, on_delete=models.CASCADE,
            related_name="ShareCertificate")
    Date = models.DateTimeField()
    Cancelled = models.BooleanField()
    FromRemainder = models.BooleanField()
    FromPerson = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE,
            related_name = "FromPersonShareCertificate")
    FromCompany = models.ForeignKey(Company, null=True, blank=True, on_delete =models.CASCADE,
            related_name = "FromCompanyShareCertificate")
    ToPerson = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE,
            related_name = "ToPersonShareCertificate")
    ToCompany = models.ForeignKey(Company, null=True, blank=True, on_delete =models.CASCADE,
            related_name = "ToCompanyShareCertificate")
    CertificateNumber = models.CharField(max_length=200, null=True, blank=True)
    Transfer = models.ForeignKey(Transfer, null=True, blank=True, on_delete=models.CASCADE,
            related_name = "ShareCertificate")
    class Meta:
        verbose_name_plural = "ShareCertificates"

    def __str__(self):
        if self.FromRemainder:
            _from = "remainder"
        else:
            _from = self.FromPerson or self.FromCompany
        _to = self.ToPerson or self.ToCompany

        if self.Ammount.is_integer():
            ammount = int(self.Ammount)
        else:
            ammount = self.Ammount
        return str(ammount) + " " + str(self.ShareClass) + " shares from " \
                +str(_from) + " to " + str(_to)
    











