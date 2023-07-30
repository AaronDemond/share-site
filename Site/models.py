from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

class Person(models.Model):
    Name = models.CharField(max_length=500)
    Address = models.CharField(max_length=500)
    Created = models.DateTimeField(editable=False)
    Modified= models.DateTimeField()

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Person, self).save(*args, **kwargs)

    def __str__(self):
        return self.Name
    
class Company(models.Model):
    Name = models.CharField(max_length=500)
    Created = models.DateTimeField(editable=False)
    Modified= models.DateTimeField()

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        if self.Name == "":
            raise Exception("Can't be a blank name")
        else:
            super(Company, self).save(*args, **kwargs)

    def __str__(self):
        return self.Name



class Manager(models.Model):

    titles = [
            ("Officer", "Officer"),
            ("President", "President"), 
            ("Secretary", "Secretary"),
            ("VP", "VP"),
            ("Other", "Other")
            ]
    Person = models.ForeignKey(Person, on_delete=models.CASCADE, unique = False,
            related_name = "Manager")
    Title = models.CharField(max_length=200, choices=titles)
    Company = models.ForeignKey(Company, on_delete=models.CASCADE, unique = False,
            related_name = "Manager")

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
    Ammount = models.IntegerField()
    ShareClass = models.ForeignKey(ShareClass, on_delete=models.CASCADE,
            related_name="AuthorizedShares")
    Date = models.DateTimeField()

    def save(self, *args, **kwargs):
        if int(self.Ammount) < 0:
            raise Exception("Must be above zero")
        else:
            super(AuthorizedShares, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.Ammount) + " of " + str(self.ShareClass) + " for " + str(self.Company)

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
    Ammount = models.IntegerField()
    ShareClass = models.ForeignKey(ShareClass, on_delete =models.CASCADE)
    Price = models.FloatField()

    def __str__(self):
        _from = self.FromPerson or self.FromCompany
        _to = self.ToPerson or self.ToCompany
        return str(self.Ammount) + " from " + _from.Name + " to " + _to.Name
            


    











