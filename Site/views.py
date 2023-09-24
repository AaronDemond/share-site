from django.http import HttpResponse
import functools
import pytz
from django.db.models import Q
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, HttpResponse, HttpResponseRedirect 
from Site.models import Company, ShareClass, AuthorizedShares, Person, Transfer, CompanyParticipant, Manager, ManagerRole, ShareCertificate
from django.urls import resolve
from django.utils import timezone


PAGELENGTH = 7


#Home page
def index(request, **kwargs):
    if request.user.is_authenticated:
        return render(request, 'index.html', {})
    else:
        return HttpResponse("Please Login")

def companies(request, company_id=None, context=None):
    if request.user.is_authenticated:
        if context is None:
            context = {}
        query = request.GET.get('query', None)
        if query:
            ql = Company.objects.filter(Name__icontains=query).order_by("Name")
            context['query'] = query
        else:
            ql = Company.objects.all().order_by("Name")
            context['query'] = ""

        context['companies'] = ql

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(ql):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        context['companies'] = context['companies'][start:end]
        context['page'] = page

        context["error_type"] = request.GET.get("alertType")
        context["alert"] = request.GET.get("alert")

        return render(request, 'companies.html', context)
    else:
        return HttpResponse("Please Login")

def shareholders_register(request, company_id=None):
    if request.user.is_authenticated:
        context = {}
        return render(request, 'shareholders_register.html', context)
    else:
        return HttpResponse("Please Login")
    
def people(request, context={}):
    if request.user.is_authenticated:
        if "companyCreatedAlert" not in context.keys() \
                and "personCreatedAlert" not in context.keys() \
                and "linkAlert" not in context.keys():
            context["alert_type"] = None
            context["alert"] = None
        if request.method == "POST":
            _type = request.POST.get("type")
            entity_id = request.POST.get("entity_id")
            address = request.POST.get("Address")
            name = request.POST.get("Name")

            try:
                if _type == "person":
                    person = Person.objects.get(pk=entity_id)
                    others = Person.objects.filter(Name=name)
                    others = [x for x in others if int(x.pk) != int(entity_id)]
                    if len(others) > 0:
                        raise Exception("Person Already Exists")
                    person.Name = name
                    person.Address = address
                    person.save()
                elif _type == "company":
                    company = Company.objects.get(pk=entity_id)
                    date = request.POST.get("date")
                    time = request.POST.get("time")
                    dt = date + " " + time
                    date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                    #date = pytz.timezone("America/Halifax").localize(date)
                    company.Name = name
                    company.Address = address
                    company.IncorporationDate = date
                    auth_shares = AuthorizedShares.objects.filter(Company=company)
                    others = Company.objects.filter(Name=name)
                    others = [x for x in others if int(x.pk) != int(entity_id)]
                    if len(others) > 0:
                        raise Exception("Company Already Exists")
                    for auth in auth_shares:
                        if auth.Date < date:
                            raise Exception("Cannot incorporate after authorizing shares")
                    managers = company.Manager.all()
                    for manager in managers:
                        if manager.StartDate < date:
                            raise Exception("Cannot incorporate after management added")
                    company.save()
                return HttpResponseRedirect("/entities/" + \
                    "?alert=Entity%20Updated&alertType=success")
            except Exception as e:
                error = str(e).replace(" ", "%20")
                return HttpResponseRedirect("/entities/" + \
                    "?alert="+error+"&alertType=danger")
        if request.GET.get("entity_id"):
            _type = request.GET.get("type")
            _id = request.GET.get("entity_id")
            if _type == "person":
                entity = Person.objects.get(pk=_id)
            elif _type == "company":
                entity = Company.objects.get(pk=_id)
            context["entity"] = entity
            context["type"] = _type

            if request.GET.get("delete") == "true":
                #Delete all transfers that become impossible if person is deleted
                #if _type == "person":
                if _type:
                    companies = set()
                    if _type == "person":
                        transfers = Transfer.objects.filter(Q(ToPerson = entity) | \
                                Q(FromPerson = entity))
                    else:
                        transfers = Transfer.objects.filter(Q(ToCompany = entity) | \
                                Q(FromCompany = entity))
                    for t in transfers:
                        companies.add(t.Company)
                    to_be_deleted = []
                    for company in companies:

                        #get share classes for each company
                        _transfers = Transfer.objects.filter(Company = company)
                        if _type == "person":
                            _transfers = [x for x in _transfers if x.ToPerson != entity \
                                    and x.FromPerson != entity]
                        else:
                            _transfers = [x for x in _transfers if x.ToCompany != entity \
                                    and x.FromCompany != entity]
                        _transfers.sort(key= lambda x: x.Date)
                        shareClassSet = set([x.ShareClass for x in _transfers])

                        #get sorted transfers not linked to selected entity 
                        #and initalize their register to 0
                        for shareClass in shareClassSet:
                            auth_shares = list(AuthorizedShares.objects.filter( \
                                    Company=company, ShareClass=shareClass))
                            _transfers = Transfer.objects.filter(Company = company, \
                                    ShareClass = shareClass)
                            if _type == "person":
                                _transfers = [x for x in _transfers if x.ToPerson != entity \
                                        and x.FromPerson != entity]
                            else:
                                _transfers = [x for x in _transfers if x.ToCompany != entity \
                                        and x.FromCompany != entity]
                                
                            _transfers.extend(auth_shares)
                            _transfers.sort(key= lambda x: x.Date)

                            to_be_deleted.extend(getToBeDeletedTransfers(_transfers,
                                company))

                    context["transfers"] = to_be_deleted

                    #Add back transfers that are selected for deletion
                    _transfers = Transfer.objects.filter(Company__in = companies)
                    if _type == "person":
                        context["transfers"].extend([x for x in _transfers if \
                                x.ToPerson == entity or x.FromPerson == entity])
                    else:
                        context["transfers"].extend([x for x in _transfers if \
                                x.ToCompany == entity or x.FromCompany == entity])

                    #Sort by name and then time
                    context["transfers"].sort(key= lambda x: x.Date)
                    sorted_transfers = []
                    companies = list(companies)
                    companies.sort(key = lambda x: x.Name)
                    for company in companies:
                        transfer_list = []
                        for transfer in context["transfers"]:
                            if transfer.Company == company:
                                transfer_list.append(transfer)
                        transfer_list.sort(key = lambda x: x.Date, reverse = True)
                        sorted_transfers.append(transfer_list)
                    sorted_transfers_flat = []
                    for row in sorted_transfers:
                        sorted_transfers_flat.extend(row)

                    context["transfers"] = sorted_transfers_flat

                    #context["transfers"].append(entity)
                    if _type == "person":
                        context["type"] = "person"
                    else:
                        context["type"] = "company"

                context["entity"] = entity
                return render(request, "delete_person_confirm.html", context)
                return HttpResponseRedirect("/entities/" + \
                    "?alert=Entity%20Deleted&alertType=success")
            if request.GET.get("edit") == "true":
                context["edit"] = True
                if _type == "person":
                    return render(request, "create_person.html", context)
                if _type == "company":
                    dt = entity.IncorporationDate
                    #dt = dt - datetime.timedelta(hours=3)
                    date = dt.strftime("%Y-%m-%d")
                    time = dt.strftime("%H:%M:%S")
                    context["entity"].Date = date
                    context["entity"].Time = time
                    return render(request, "create_company.html", context)

        query = request.GET.get('query', None)
        context["filteredBy"] = False
        ql = []
        if query:
            people = Person.objects.filter(Name__icontains=query).order_by("-pk")
            companies = Company.objects.filter(Name__icontains=query).order_by("-pk")
            context['query'] = query
        else:
            people = Person.objects.all().order_by("-pk")
            companies = Company.objects.all().order_by("-pk")
            context['query'] = ""

        for p in people:
            ql.append([p,"person"])
        for c in companies:
            ql.append([c, "company"])
        ql.sort(key=lambda x: x[0].Name)

        if request.GET.get("type"):
            filtered_ql = []
            if request.GET.get("type") == "person":
                context["filteredBy"] = "person"
                for entity in ql:
                    if isinstance(entity[0], Person):
                        filtered_ql.append([entity[0], "person"])
            if request.GET.get("type") == "company":
                context["filteredBy"] = "company"
                for entity in ql:
                    if isinstance(entity[0], Company):
                        filtered_ql.append([entity[0], "company"])
            ql = filtered_ql


        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(ql):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        ql = ql[start:end]

        context['entities'] = ql
        context['page'] = page

        if request.GET.get("alert"):
            context["alert"] = request.GET.get("alert")
            context["alert_type"] = request.GET.get("alertType")

        return render(request, 'people.html', context)
    else:
        return HttpResponse("Please Login")

def delete_entity(request):
    if request.user.is_authenticated:
        selected = request.POST.getlist("confirm")
        if request.POST.get("type") == "person":
            entity = Person.objects.get(pk=request.POST.get("entity"))
        else:
            entity = Company.objects.get(pk=request.POST.get("entity"))
        try:
            to_delete = Transfer.objects.filter(pk__in = selected)
            companies = set()
            for x in to_delete:
                companies.add(x.Company)
            to_delete.delete()
            entity.delete()
            for company in companies:
                transfers = Transfer.objects.filter(Company = \
                        company).order_by("Date")
                shareClasses = set([x.ShareClass for x in transfers])
                for shareClass in shareClasses:
                    shareCerts = ShareCertificate.objects.filter(ShareClass = \
                            shareClass, ReferenceCompany = company)
                    shareCerts.delete()
                    t = Transfer.objects.filter(Company = company,
                            ShareClass = shareClass).order_by("Date")
                    for tran in t:
                        create_certificates(tran)
            return HttpResponseRedirect("/entities/" + \
                "?alert=Entity%20Deleted&alertType=success")

        except Exception as e:
            error = str(e).replace(" ", "%20")
            return HttpResponseRedirect("/entities/" + \
                "?alert="+error+"&alertType=danger")
    else:
        return HttpResponse("Please Login")

def link(request, _id=None):
    if request.user.is_authenticated:
        _type = request.GET.get("type")
        context = {}
        if _type == "person":
            context["entity"] = Person.objects.get(pk=_id)
        elif _type == "company":
            context["entity"] = Company.objects.get(pk=_id)
        if request.GET.get("search"):
            query = request.GET.get("query")
            companies = Company.objects.filter(Name__icontains=query).order_by("Name")
            context["query"] = query
        else:
            companies = Company.objects.all().order_by("Name")
            context["query"] = ""

        if request.GET.get("company_id"):
            company = Company.objects.get(pk=request.GET.get("company_id"))
            companyReference = company
            companyParticipant = CompanyParticipant(CompanyReference=companyReference)
            if _type == "person":
                companyParticipant.LinkedPerson = context["entity"]
                q = CompanyParticipant.objects.filter(CompanyReference = company,
                        LinkedPerson = context["entity"])
                if len(q) > 0:
                    return HttpResponseRedirect("/entities/" + \
                        "?alert=Link%20Already%20Exists&alertType=danger")

            elif _type == "company":
                companyParticipant.LinkedCompany = context["entity"]
                q = CompanyParticipant.objects.filter(CompanyReference = company,
                        LinkedCompany = context["entity"])
                if len(q) > 0:
                    return HttpResponseRedirect("/entities/" + \
                        "?alert=Link%20Already%20Exists&alertType=danger")
            try:
                companyParticipant.save()
                return HttpResponseRedirect("/entities/" + \
                        "?alert=Entity%20Linked&alertType=success")
            except:
                context["alert_type"] = "danger"
                context["alert"] = "Error saving link"
                context["linkAlert"] = True
                return people(request, context)
        context["companies"] = companies 
        context["type"] = _type

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(context['companies']):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        context['page'] = page
        context['companies'] = context['companies'][start:end]

        return render(request, "link.html", context)
    else:
        return HttpResponse("Please Login")

def issue_shares(request, company_id=None):
    if request.user.is_authenticated:
        current_url = resolve(request.path_info).url_name
        company = Company.objects.get(pk=int(company_id))
        share_classes = ShareClass.objects.all().order_by("Name")
        context = {'company' : company}
        incorpDate = company.IncorporationDate
        #incorpDate = incorpDate - datetime.timedelta(hours=3)
        incorpDate = incorpDate.strftime("%Y-%m-%d %H:%M:%S")
        context["incorporationDate"] = incorpDate

        #Creates a dict of type {'Share Class' : [Ammount, Document, Issued, Remaining, par value]}
        authorized = company.AuthorizedShares.all()
        share_classes_authorized = {}
        shareClassSet = set()
        #initalize dict with share classes as key
        for t in authorized:
            if t.ShareClass not in share_classes_authorized.keys():
                share_classes_authorized[str(t.ShareClass)] = [0]
        #Increment the corrosponding dict by the authorized ammount and append Document
        #if needed
        for t in authorized:
            share_classes_authorized[str(t.ShareClass)][0] += t.Ammount
            shareClassSet.add(t.ShareClass)
            if t.Document:
                if len(share_classes_authorized[str(t.ShareClass)]) == 2:
                    share_classes_authorized[str(t.ShareClass)][1].append(t.Document)
                else:
                    share_classes_authorized[str(t.ShareClass)].append([t.Document])
            else:
                if len(share_classes_authorized[str(t.ShareClass)]) == 1:
                    share_classes_authorized[str(t.ShareClass)].append([None])
                else:
                    share_classes_authorized[str(t.ShareClass)][1].append(None)

        #Subtract transfers bought back by the company
        transfers = Transfer.objects.filter(Company=company, ToCompany=company)
        for t in transfers:
            if len(share_classes_authorized)>0:
                share_classes_authorized[str(t.ShareClass)][0] -= t.Ammount

        #initalize issued and remaining
        transfers = Transfer.objects.filter(Company=company)
        #for t in authorized:
        for sc in shareClassSet:
            share_classes_authorized[str(sc)].append(0)
            share_classes_authorized[str(sc)].append(0)

        #calculate issued
        for t in transfers:
            if t.FromCompany == company:
                share_classes_authorized[str(t.ShareClass)][2] += t.Ammount
            if t.ToCompany == company:
                share_classes_authorized[str(t.ShareClass)][2] -= t.Ammount

        #calculate remaining
        for shareClass in shareClassSet:
            share_classes_authorized[str(shareClass)][3] = \
                    share_classes_authorized[str(shareClass)][0] - \
                    share_classes_authorized[str(shareClass)][2]

        for sc in shareClassSet:
            auth = AuthorizedShares.objects.filter(ShareClass = sc, Company = company)[0]
            share_classes_authorized[str(sc)].append(auth.Value)

        for key, value in share_classes_authorized.items():
            if value[0] != 0:
                if value[0].is_integer():
                    v = int(value[0])
                    v = f'{v:,}'
                    share_classes_authorized[key][0] = v
            if value[2] != 0:
                if value[2].is_integer():
                    v = int(value[2])
                    v = f'{v:,}'
                    share_classes_authorized[key][2] = v
            if value[3] != 0:
                if value[3].is_integer():
                    v = int(value[3])
                    v = f'{v:,}'
                    share_classes_authorized[key][3] = v
            if value[4] != 0:
                if value[4].is_integer():
                    v = int(value[4])
                    v = f'{v:,}'
                    share_classes_authorized[key][4] = v


                

        context['share_classes'] = share_classes
        context['share_classes_authorized'] = share_classes_authorized

        _all_auth = AuthorizedShares.objects.filter(Company = company)
        context['authorized_classes'] = set([x.ShareClass for x in _all_auth])


        #Either a share issue request or a file upload
        if request.method == "POST":
            #File upload linked to a share class
            if request.POST.get("append") == "True":
                try:
                    _file = request.FILES["appendedFile"]
                    share_class = request.POST.get("ShareClass")
                    share_class = ShareClass.objects.get(pk=share_class)
                    authorized_shares = AuthorizedShares.objects.filter(ShareClass=share_class,
                            Company = company)
                    #remove previous documents
                    for a in authorized_shares:
                        if a.Document is not None:
                            a.Document = None
                            a.save()
                    #add new document
                    authorized_shares_obj = authorized_shares[0]
                    authorized_shares_obj.Document = _file
                    authorized_shares_obj.save()
                    return HttpResponseRedirect("/companies/" + str(company.pk)  + \
                    "/issue/?alert=Document Appended&alertType=success")
                except Exception as e:
                    if str(e) == "'appendedFile'":
                        return HttpResponseRedirect("/companies/" + str(company.pk) + \
                        "/issue/?alert=No File Attached&alertType=danger")
                    if str(e) == "invalid literal for int() with base 10: 'Choose...'":
                        return HttpResponseRedirect("/companies/" + str(company.pk) + \
                        "/issue/?alert=No Share Class Selected&alertType=danger")
                    if str(e) == "list index out of range":
                        return HttpResponseRedirect("/companies/" + str(company.pk) + \
                        "/issue/?alert=No Shares Of That Type Authorized&alertType=danger")
                    return HttpResponseRedirect("/companies/" + str(company.pk) + \
                    "/issue/?alert=" + str(e) + "&alertType=danger")

            #Authorize shares request
            share_class = request.POST.get('ShareClass')
            ammount = request.POST.get('Ammount')
            date = request.POST.get("date")
            time = request.POST.get("time")
            value = request.POST.get("parValue")
            dt = date + " " + time
            if len(request.FILES) != 0:
                _file = request.FILES["uploadedFile"]
            else:
                _file = False
            

            if share_class and ammount and date and time:
                if float(ammount) < 0:
                    return HttpResponseRedirect("/companies/" + str(company.pk) + \
                    "/issue/?alert=Cannot Issue Negative Shares&alertType=danger")

                try:
                    share_class = ShareClass.objects.get(pk=share_class)
                    date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                    #date = pytz.timezone("America/Halifax").localize(date)
                    if _file:
                        authorized_shares = AuthorizedShares(Company=company,
                                Ammount=float(ammount), ShareClass=share_class,
                                Date=date, Value=value, Document=_file)
                    else:
                        authorized_shares = AuthorizedShares(Company=company,
                                Ammount=float(ammount), ShareClass=share_class,
                                Date=date, Value=value)
                    if company.IncorporationDate > date:
                        raise Exception("Company not yet incorporated")

                    authorized_shares.save()
                    return HttpResponseRedirect("/companies/" + str(company.pk) + \
                    "/issue/?alert=Shares%20Authorized&alertType=success")

                except Exception as e:
                    return HttpResponseRedirect("/companies/" + str(company.pk) + \
                    "/issue/?alert=" + str(e) + "&alertType=danger")
            else:
                context["error_type"] = "danger"
                context["alert"] = "ERROR! Please fill the entire form"

        if request.GET.get("alertType"):
            context["error_type"] = request.GET.get("alertType")
            context["alert"] = request.GET.get("alert")
        return render(request, 'issue_shares.html', context)
    else:
        return HttpResponse("Please Login")

def create_company(request):
    if request.user.is_authenticated:
        context = {}
        if request.method == "POST":
            try:
                name = request.POST.get("Name")
                modified = datetime.datetime.now(tz=None)
                #modified = pytz.timezone("America/Halifax").localize(modified)
                date = request.POST.get("date")
                time = request.POST.get("time")
                address = request.POST.get("Address")
                if not name or not date or not time or not address:
                    raise Exception("Fill Out Entire Form")
                dt = date + " " + time
                date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                #date = pytz.timezone("America/Halifax").localize(date)
            except Exception as e:
                error = str(e)
                return HttpResponseRedirect("/entities/" + \
                        "?alert="+error+"&alertType=danger")
            try:
                new_company = Company(Name=name,
                        IncorporationDate=date, Address=address,
                        Modified=modified)
                others = Company.objects.filter(Name=name)
                if len(others) > 0:
                    return HttpResponseRedirect("/entities/" + \
                        "?alert=Company%20Exists&alertType=danger")
                else:
                    new_company.save()
                    return HttpResponseRedirect("/entities/" + \
                        "?alert=Company%20Created&alertType=success")
            except Exception as e:
                error = str(e)
                return HttpResponseRedirect("/entities/" + \
                        "?alert="+error+"&alertType=danger")

        return render(request, 'create_company.html', context)
    else:
        return HttpResponse("Please Login")

def create_person(request):
    if request.user.is_authenticated:
        context = {}
        if request.method == "POST":
            try:
                name = request.POST.get("Name")
                others = Person.objects.filter(Name=name)
                if len(others) > 0:
                    raise Exception("Name already in use")
                address = request.POST.get("Address")
                date = datetime.datetime.now()
                #date = pytz.timezone("America/Halifax").localize(date)
                new_person = Person(Name = name, Address = address, 
                        Modified=date)
                new_person.save()
                return HttpResponseRedirect("/entities/" + \
                        "?alert=Person%20Created&alertType=success")
            except Exception as e:
                error = str(e)
                return HttpResponseRedirect("/entities/" + \
                        "?alert="+error+"&alertType=danger")

        return render(request, 'create_person.html', context)
    else:
        return HttpResponse("Please Login")

#Accepts date sorted transfer list that includes authorizations
#and a target company and returns a list of all transfers that are
#impossible
def getToBeDeletedTransfers(_transfers, company):
    to_be_deleted = []
    participants = company.Participant.all()
    register = {}
    for p in participants:
        if p.LinkedPerson:
            register[p.LinkedPerson] = 0
        if p.LinkedCompany:
            register[p.LinkedCompany] = 0

    #authorized, issued, remaining
    register[company] = [0,0,0]
    for t in _transfers:
        if isinstance(t, AuthorizedShares):
            register[company][0] += t.Ammount
            register[company][2] += t.Ammount
        else:
            receiver = t.ToPerson or t.ToCompany
            sender = t.FromPerson or t.FromCompany
            if receiver == company:
                if register[sender] >= t.Ammount:
                    register[company][0] -= t.Ammount
                    register[company][1] -= t.Ammount
                    register[company][2] = register[company][0] - \
                            register[company][1]
                    register[sender] -= t.Ammount
                else:
                    to_be_deleted.append(t)

            elif sender == company:
                if register[company][2] >= t.Ammount:
                    register[company][1] += t.Ammount
                    register[company][2] = register[company][0] - \
                            register[company][1]
                    register[receiver] += t.Ammount
                else:
                    to_be_deleted.append(t)
            else:
                if register[sender] >= t.Ammount:
                    register[sender] -= t.Ammount
                    register[receiver] += t.Ammount
                else:
                    to_be_deleted.append(t)
    to_be_deleted.sort(key = lambda x: x.Date, reverse = True)
    return to_be_deleted

def authorized(request, company_id=None, context={}):
    company = Company.objects.get(pk=company_id)
    authorizedShares = AuthorizedShares.objects.filter(Company=company).order_by("-Date")
    if request.GET.get("query"):
        query = request.GET.get("query")
        authorizedShares = [x for x in authorizedShares if query.lower() in x.__str__().lower()]
        context["query"] = query
    context["authorizedShares"] = authorizedShares
    for a in context["authorizedShares"]:
        if a.Ammount.is_integer():
            ammount = int(a.Ammount)
        else:
            ammount = a.Ammount
        ammount = f'{ammount:,}'
        a.ammountFormatted = ammount
        a.dateFormatted = a.Date.strftime("%Y-%m-%d %H:%M:%S")

    context["company"] = company

    context["error_type"] = None
    context["alert"] = None

    if request.method == "POST":

        try:
            authToDeleteId = request.POST.get("authToDelete")
            tranToDeleteIds = request.POST.getlist("transfers")
            tranToDelete = Transfer.objects.filter(pk__in=tranToDeleteIds)
            authToDelete = AuthorizedShares.objects.get(pk=authToDeleteId)
            shareClass = authToDelete.ShareClass
            company = authToDelete.Company
            tranToDelete.delete()
            authToDelete.delete()

            shareCerts = ShareCertificate.objects.filter(ShareClass=shareClass,
                    ReferenceCompany = company)
            shareCerts.delete()
            transfers = Transfer.objects.filter(ShareClass=shareClass, 
                    Company=company).order_by("Date")
            for t in transfers:
                create_certificates(t)


            return HttpResponseRedirect("/companies/" + str(company.pk) + "/authorized/" + \
                    "?alertType=success&alert=Authorization Deleted")
        except Exception as e:
            error = str(e)
            return HttpResponseRedirect("/companies/" + str(company.pk) + "/authorized/" + \
                    "?alert=ERROR: "+error+"&alertType=danger")

        return companies(request, context = context)

    if request.GET.get("delete") == "True":
        authorizedToDelete = request.GET.get("auth_id")
        authorizedToDelete = AuthorizedShares.objects.get(pk=authorizedToDelete)
        shareClass = authorizedToDelete.ShareClass
        company = authorizedToDelete.Company
        context["authorizedToDelete"] = authorizedToDelete

        _transfers = list(Transfer.objects.filter(Company=company, 
            ShareClass=shareClass).order_by("Date"))
        auth_shares = list(AuthorizedShares.objects.filter(Company=company, 
            ShareClass=shareClass))
        auth_shares.remove(authorizedToDelete)
        _transfers.extend(auth_shares)
        _transfers.sort(key= lambda x: x.Date)

        
        context["toDelete"] = getToBeDeletedTransfers(_transfers, company)

        return render(request, "authorizedDeleteConfirm.html", context)

    if request.GET.get("page"):
        page = int(request.GET.get("page"))
    else:
        page = 1
    start = (page - 1) * PAGELENGTH
    end = start + PAGELENGTH

    if end < len(context['authorizedShares']):
        context["hasNextPage"] = True
    else:
        context["hasNextPage"] = False

    if request.GET.get("alertType"):
        context["error_type"] = request.GET.get("alertType")
        context["alert"] = request.GET.get("alert")

    context['authorizedShares'] = context['authorizedShares'][start:end]
    context['page'] = page

    #show list of authorizations
    return render(request, "authorized.html", context)

def transfers(request, company_id=None, transfer_id=None,context={}):
    if request.user.is_authenticated:

        context["alert"] = None
        context["alert_type"] = None
        company = Company.objects.get(pk=company_id)
        _transfers = list(Transfer.objects.filter(Company=company).order_by("-Date"))
        context["transfers"] = []
        context["company"] = company

        #escape quotes for html
        for t in _transfers:
            t.str = t.__str__()
            s = ""
            for char in t.str:
                if char =='"' :
                    s += "&quot;"
                else:
                    s += char
            t.str = s
            context["transfers"].append(t)
        for t in context["transfers"]:
            t.From = t.FromCompany or t.FromPerson
            t.To = t.ToPerson or t.ToCompany
            t.D = t.Date.strftime("%Y-%m-%d %H:%M:%S")
            if t.Ammount.is_integer():
                ammount = int(t.Ammount)
            else:
                ammount = t.Ammount
            t.ammountFormatted = f'{ammount:,}'

        tt=[]
        if request.GET.get("query"):
            query = request.GET.get("query").lower()
            for t in _transfers:
                if query in t.__str__().lower():
                    tt.append(t)
            context['transfers'] = tt
            context['query'] = query
        else:
            context['query'] = ""

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(context['transfers']):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        context['transfers'] = context['transfers'][start:end]
        context['page'] = page

        #User confirmed deletion of impossible transfers
        if request.POST.get("confirm"):
            try:
                selected = request.POST.getlist("confirm")
                to_delete = Transfer.objects.filter(pk__in=selected)
                shareClass = to_delete[0].ShareClass
                company = to_delete[0].Company
                to_delete.delete()
                context['error_type'] = "success"
                context['alert'] = "Transfers deleted"
                shareCerts = ShareCertificate.objects.filter(ShareClass=shareClass,
                        ReferenceCompany = company)
                shareCerts.delete()
                transfers = Transfer.objects.filter(ShareClass=shareClass, 
                        Company=company).order_by("Date")
                for t in transfers:
                    create_certificates(t)

                return HttpResponseRedirect("/companies/" +str(company.id) + \
                    "/transfers/?alert=Transfer(s)%20Deleted&alertType=success")

            except Exception as e:
                error = str(e)
                return HttpResponseRedirect("/companies/" +str(company.id) + \
                    "/transfers/?alert="+error+"&alertType=danger")

        #Get list of impossible transfers
        if request.POST.get("selectedTransfer"):
            transfer_id = request.POST.get("selectedTransfer")
            share_type_id = request.POST.get("selectedShareType")
            shareClass = ShareClass.objects.get(pk=share_type_id) 
            _transfers = list(Transfer.objects.filter(Company=company, ShareClass=shareClass).order_by("Date"))
            transfer = Transfer.objects.get(pk=transfer_id)
            _transfers.remove(transfer)
            auth_shares = list(AuthorizedShares.objects.filter(Company=company, ShareClass=shareClass))
            _transfers.extend(auth_shares)
            _transfers.sort(key= lambda x: x.Date)

            to_be_deleted = getToBeDeletedTransfers(_transfers, company)
            to_be_deleted.append(transfer)


            context["transfers"] = to_be_deleted
            return render(request, 'transfers_confirm.html', context)
        if request.GET.get("alert"):
            context["alert"] = request.GET.get("alert")
            context["alert_type"] = request.GET.get("alertType")
        return render(request, 'transfers.html', context)
    else:
        return HttpResponse("Please Login")

def enter_transfer(request, company_id=None):
    if request.user.is_authenticated:
        company = Company.objects.get(pk=int(company_id))
        participants = company.Participant.all()
        share_classes = ShareClass.objects.all().order_by("Name")
        auth_shares = AuthorizedShares.objects.filter(Company=company)
        share_classes_set = set()
        for a in auth_shares:
            share_classes_set.add(a.ShareClass)
        share_classes = list(share_classes_set)
        share_classes.sort(key = lambda x: x.Name)
        context = {}
        context['company']=company
        context['share_classes']=share_classes
        def compare(item1, item2):
            item1 = item1.LinkedPerson or item1.LinkedCompany
            item2 = item2.LinkedPerson or item2.LinkedCompany

            if item1.Name < item2.Name:
                return 1
            elif item1.Name > item2.Name:
                return -1
            else:
                return 0

        participants = list(participants)
        participants.sort(key=functools.cmp_to_key(compare), reverse=True)
        context['participants']=participants
        if request.GET.get('type') == 'search':
            context['participants'] = []
            query = request.GET.get('query').lower()
            context['query']=query
            for p in participants:
                if p.LinkedPerson:
                    if query in p.LinkedPerson.Name.lower():
                        context['participants'].append(p)
                elif p.LinkedCompany:
                    if query in p.LinkedCompany.Name.lower():
                        context['participants'].append(p)
                context['participants'].sort(key=functools.cmp_to_key(compare), reverse=True)

        direction = request.GET.get('direction')
        targetDiv = request.GET.get('targetDiv')
        context['direction'] = direction
        context['targetDiv'] = targetDiv
        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(context['participants']):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        context['participants'] = context['participants'][start:end]

        context['page'] = page
        if request.GET.get('type') == 'search':
            return render(request, 'enter_transfer_search.html', context)

        if request.method=="POST":
            try:
                date = request.POST.get("date")
                time = request.POST.get("time")
                dt = date + " " + time
                date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                #date = pytz.timezone("America/Halifax").localize(date)
                price = request.POST.get("price")
                ammount = request.POST.get("ammount")
                shareClass = request.POST.get("shareClass")
                shareClass = ShareClass.objects.get(pk=shareClass)

                other = Transfer.objects.filter(Date=date)
                if len(other) > 0 :
                    raise Exception("Transaction Exists at This Time")

                transfer = Transfer(Date=date,Price=price,Ammount=ammount,
                        Company=company,ShareClass=shareClass)

                fromCompany = request.POST.get("fromCompany")
                fromPerson = request.POST.get("fromPerson")
                toPerson = request.POST.get("toPerson")
                toCompany = request.POST.get("toCompany")
                if fromCompany and toCompany:
                    if fromCompany == toCompany:
                        raise Exception("Origin same as destination")
                if fromPerson and toPerson:
                    if fromPerson == toPerson:
                        raise Exception("Origin same as destination")
                if fromPerson:
                    fromPerson = Person.objects.get(pk=fromPerson)
                    transfer.FromPerson = fromPerson
                elif fromCompany:
                    fromCompany = Company.objects.get(pk=fromCompany)
                    transfer.FromCompany = fromCompany
                else:
                    raise Exception("Select an origin")
                if toPerson:
                    toPerson = Person.objects.get(pk=toPerson)
                    transfer.ToPerson = toPerson
                elif toCompany:
                    toCompany = Company.objects.get(pk=toCompany)
                    transfer.ToCompany = toCompany
                else:
                    raise Exception("Select a destination")
            except Exception as e:
                error = str(e)
                return HttpResponseRedirect("/companies/" +str(company.id) + \
                        "/enterTransfer/?alert=ERROR: "+error+"&alertType=danger")

            def checkEnoughShares(t):
                if t == "person":
                    transfers = Transfer.objects.filter(Q(FromPerson \
                    = fromPerson, ShareClass=shareClass, Company=company) |\
                    Q(ToPerson = fromPerson, ShareClass=shareClass,
                        Company=company)).order_by('Date')
                    transfers = list(transfers)
                    total = 0
                    newInserted = False
                    for t in transfers:
                        if t.Date > date and newInserted == False:
                            total -= float(ammount)
                            newInserted = True
                            if total < 0:
                                return False
                        if t.ToPerson == fromPerson:
                            total += t.Ammount
                        elif t.FromPerson == fromPerson:
                            total -= t.Ammount
                        if total < 0:
                            return False
                    if newInserted == False:
                        total -= float(ammount)
                        if total < 0:
                            return False
                    return True

                if t == "company":
                    if company == fromCompany:
                        auth_shares = AuthorizedShares.objects.filter(Company=company,
                                ShareClass=shareClass)
                        total = 0
                        transfers = Transfer.objects.filter(FromCompany \
                            = company, ShareClass=shareClass, 
                            Company=company).order_by('Date')
                        all_tran = []
                        all_tran.extend(list(transfers))
                        all_tran.extend(list(auth_shares))
                        transfers = list(transfers)
                        all_tran.sort(key = lambda x: x.Date)
                        newInserted = False
                        for t in all_tran:
                            if t.Date > date and newInserted == False:
                                total -= float(ammount)
                                newInserted = True
                                if total < 0:
                                    return False
                            if isinstance(t, AuthorizedShares):
                                total += t.Ammount
                            else:
                                total -= t.Ammount
                            if total < 0:
                                return False
                        if newInserted == False:
                            total -= float(ammount)
                            if total < 0:
                                return False
                        return True
                    else:
                        transfers = Transfer.objects.filter(Q(FromCompany \
                        = fromCompany, ShareClass=shareClass,
                        Company=company) | Q(ToCompany = fromCompany, 
                            Company=company, ShareClass=shareClass)).order_by('Date')
                        total = 0
                        newInserted = False
                        for t in transfers:
                            if t.Date > date and newInserted == False:
                                total -= float(ammount)
                                newInserted = True
                                if total < 0:
                                    return False
                            if t.ToCompany == fromCompany:
                                total += t.Ammount
                            elif t.FromCompany == fromCompany:
                                total -= t.Ammount
                            if total < 0:
                                return False
                        if newInserted == False:
                            total -= float(ammount)
                            if total < 0:
                                return False
                        return True

            try:
                if fromCompany:
                    enough = checkEnoughShares("company")
                elif fromPerson:
                    enough = checkEnoughShares("person")
            except Exception as e:
                error = str(e)
                return HttpResponseRedirect("/companies/" +str(company.id) + \
                    "/enterTransfer/?alert="+error+"&alertType=danger")

            if enough:
                try:
                    transfer.save()
                    context['alert_type'] = "success"
                    context['alert'] = "Transfer Saved"
                    transfer = Transfer.objects.all().latest("pk")
                    transfers = Transfer.objects.filter(ShareClass=shareClass,
                            Company=company).order_by("Date")
                    certs = ShareCertificate.objects.filter(ShareClass=shareClass, 
                            ReferenceCompany = company)
                    certs.delete()
                    for t in transfers:
                        create_certificates(t)
                    return HttpResponseRedirect("/companies/" +str(company.id) + \
                        "/enterTransfer/?alert=Transfer%20Saved&alertType=success")
                except Exception as e:
                    error = str(e)
                    return HttpResponseRedirect("/companies/" +str(company.id) + \
                        "/enterTransfer/?alert="+error+"&alertType=danger")
            else:
                return HttpResponseRedirect("/companies/" +str(company.id) + \
                    "/enterTransfer/?alert=Not%20Enough%20Shares&alertType=danger")

        if request.GET.get("alert"):
            context["alert"] = request.GET.get("alert")
            context["alert_type"] = request.GET.get("alertType")
        return render(request, 'enter_transfer.html', context)
    else:
        return HttpResponse("Please login")

def share_certificate(request, company_id = None):
    if request.user.is_authenticated:
        company = Company.objects.get(pk=company_id)
        participants = list(company.Participant.all())
        transfers = Transfer.objects.filter(Company=company)
        toFrom = set()
        context = {'company' : company}

        if request.GET.get("certId"):
            cert = ShareCertificate.objects.get(pk=request.GET.get("certId"))
            to = cert.ToPerson or cert.ToCompany
            _from = cert.FromPerson or cert.FromCompany
            date = cert.Date.strftime("%Y-%m-%d")

            if cert.Ammount.is_integer():
                cert.Ammount = int(cert.Ammount)
            cert.Ammount = f'{cert.Ammount:,}'
            context = {"cert" : cert, 'to': to, 'date': date, 'from': _from}
            context["company"] = company
            context["type"] = request.GET.get("type")
            context["id"] = request.GET.get("id")
            context["shareClassId"] = request.GET.get("shareClassId")

            auth_shares = AuthorizedShares.objects.filter(Company=company)
            auth_types = set([x.ShareClass for x in auth_shares])
            auth_types_value = {}

            #Returns a dict of type {(ShareClass,Value):Ammount)}
            for a in auth_types:
                auth_types_value[a] = set()
            for a in auth_shares:
                auth_types_value[a.ShareClass].add(a.Value)
            auth_totals = {}
            for a in auth_types:
                for value in auth_types_value[a]:
                    auth_totals[(a,value)] = 0
                    for auth in auth_shares:
                        if auth.ShareClass == a and auth.Value == value:
                            auth_totals[(a,value)] += auth.Ammount

            #Removes bought back shares from the dict created above
            for auth_type in auth_types:
                all_tran = Transfer.objects.filter(Company=company,
                        ShareClass=auth_type,ToCompany=company).order_by("Date")
                all_auth = AuthorizedShares.objects.filter(Company=company,
                        ShareClass=auth_type).order_by("Date")
                for tran in all_tran:
                    for index, auth in enumerate(all_auth):
                        if auth.Date > tran.Date:
                            toDecrease = all_auth[index-1]
                            auth_totals[(toDecrease.ShareClass,toDecrease.Value)] -= tran.Ammount
                            break
                        if index == len(all_auth) - 1:
                            toDecrease = all_auth[index]
                            auth_totals[(toDecrease.ShareClass,toDecrease.Value)] -= tran.Ammount
                            break

            #Remove trailing zeros
            auth_totals_truncated = {}
            for key, value in auth_totals.items():
                if value.is_integer():
                    v = int(value)
                else:
                    v = value
                if key[1].is_integer():
                    k1 = int(key[1])
                else:
                    k1 = key[1]
                auth_totals_truncated[(key[0],k1)] = v


            context["no_of_auth_types"] = len(auth_totals)
            context["auth_totals"] = auth_totals_truncated 
            #Specific Cert
            return render(request, "certificate.html", context)



        #Remove participants with no share certificates
        for t in transfers:
            toFrom.add(t.FromCompany or t.FromPerson)
            toFrom.add(t.ToCompany or t.ToPerson)
        if company in toFrom:
            toFrom.remove(company)
        toRemove = set()
        for p in participants:
            pp = p.LinkedPerson or p.LinkedCompany
            if pp not in toFrom:
                toRemove.add(p)
        for p in toRemove:
            participants.remove(p)

        def compare3(item1, item2):
            item1 = item1.LinkedCompany or item1.LinkedPerson
            item2 = item2.LinkedCompany or item2.LinkedPerson

            if item1.Name < item2.Name:
                return 1
            elif item1.Name > item2.Name:
                return -1
            else:
                return 0

        participants.sort(key=functools.cmp_to_key(compare3), reverse = True)
        context["participants"] = participants
        
        #id = owner.pk
        if request.GET.get("id"):
            _type = request.GET.get("type")
            shareClasses = set()
            if _type == "company":
                owner = Company.objects.get(pk=request.GET.get("id"))
                certs = ShareCertificate.objects.filter(ToCompany=owner, ReferenceCompany=company)
            if _type == "person":
                owner = Person.objects.get(pk=request.GET.get("id"))
                certs = ShareCertificate.objects.filter(ToPerson=owner, ReferenceCompany=company)
            for c in certs:
                shareClasses.add(c.ShareClass)
            if request.GET.get("classSearch"):
                query = request.GET.get("query").lower()
                context["query"] = query
                toRemove = []
                for sc in shareClasses:
                    if query not in sc.__str__().lower():
                        toRemove.append(sc)
                for sc in toRemove:
                    shareClasses.remove(sc)

            shareClasses = list(shareClasses)
            shareClasses.sort(key=lambda x: x.Name)
            context['owner'] = owner
            context['shareClasses'] = shareClasses
            context['type'] = _type
            context['id'] = owner.pk

            if request.GET.get("page"):
                page = int(request.GET.get("page"))
            else:
                page = 1
            start = (page - 1) * PAGELENGTH
            end = start + PAGELENGTH
            if end < len(context['shareClasses']):
                context["hasNextPage"] = True
            else:
                context["hasNextPage"] = False
            context['shareClasses'] = context['shareClasses'][start:end]
            context['page'] = page




            if request.GET.get("shareClassId"):
                shareClass = ShareClass.objects.get(pk=request.GET.get("shareClassId"))
                if _type == "company":
                    owner = Company.objects.get(pk=request.GET.get("id"))
                    certs = ShareCertificate.objects.filter(ToCompany=owner, ShareClass=shareClass,
                            ReferenceCompany=company)
                if _type == "person":
                    owner = Person.objects.get(pk=request.GET.get("id"))
                    certs = ShareCertificate.objects.filter(ToPerson=owner, ShareClass=shareClass,
                            ReferenceCompany=company)
                certs = list(certs)
                certs.sort(key = lambda x: x.Date, reverse=True)
                if request.GET.get("query"):
                    query = request.GET.get("query").lower()
                    context["query"] = query
                    certs = list(certs)
                    to_remove = []
                    for c in certs:
                        if query not in c.__str__().lower():
                            to_remove.append(c)
                    for c in to_remove:
                        certs.remove(c)

                context["certs"] = certs
                context["shareClassId"] = request.GET.get("shareClassId")

                if request.GET.get("page"):
                    page = int(request.GET.get("page"))
                else:
                    page = 1
                start = (page - 1) * PAGELENGTH
                end = start + PAGELENGTH
                if end < len(context['certs']):
                    context["hasNextPage"] = True
                else:
                    context["hasNextPage"] = False
                context['certs'] = context['certs'][start:end]
                context['page'] = page

                #List of certs
                return render(request, "certificate_list.html", context)
            #List of cert classes
            return render(request, 'entity_certificates.html', context)


        #handle search query
        if request.GET.get("query"):
            filteredParticipants = []
            q = request.GET.get("query")
            for p in participants:
                name = p.LinkedPerson.Name.lower() or p.LinkedCompany.Name.lower()
                if q.lower() in name:
                    filteredParticipants.append(p)
            context['participants'] = filteredParticipants
            context['query'] = q

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH
        if end < len(context['participants']):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False
        context['participants'] = context['participants'][start:end]
        context['page'] = page


        return render(request, 'certificates.html', context)
    else:
        return HttpResponse("Please Login")

def create_certificates(transfer):
    if transfer.Company != transfer.ToCompany:
        certificateTo = ShareCertificate(ReferenceCompany=transfer.Company,
                Ammount = transfer.Ammount, ShareClass = transfer.ShareClass,
                Date = transfer.Date, Cancelled = False, FromRemainder = False,
                Transfer = transfer, CertificateNumber=None)
        certificateTo = updateCertNos(certificateTo, transfer)

        if transfer.FromPerson:
            certificateTo.FromPerson = transfer.FromPerson
        if transfer.FromCompany:
            certificateTo.FromCompany = transfer.FromCompany
        if transfer.ToPerson:
            certificateTo.ToPerson = transfer.ToPerson
        if transfer.ToCompany:
            certificateTo.ToCompany = transfer.ToCompany

        certificateTo.save()
    fromTreasury = False 
    if transfer.FromPerson:
        certificates = ShareCertificate.objects.filter(ToPerson = transfer.FromPerson,
                ShareClass = transfer.ShareClass, ReferenceCompany = transfer.Company,
                Date__lt = transfer.Date, Cancelled=False).order_by("-Date")

    if transfer.FromCompany:
        certificates = ShareCertificate.objects.filter(ToCompany = transfer.FromCompany,
                ShareClass = transfer.ShareClass, ReferenceCompany = transfer.Company,
                Date__lt = transfer.Date, Cancelled=False).order_by("-Date")
        if transfer.FromCompany == transfer.Company:
            fromTreasury = True
    if fromTreasury == False:
        runningTotal = float(transfer.Ammount)
        for c in certificates:
            c.Cancelled = True
            c.save()
            if runningTotal == c.Ammount:
                break
            elif runningTotal > c.Ammount:
                runningTotal -= c.Ammount
            elif runningTotal == 0:
                break
            else:
                newTotal = c.Ammount - runningTotal
                newDate = transfer.Date + datetime.timedelta(seconds = 5)
                certificateFrom = ShareCertificate(ReferenceCompany=transfer.Company,
                    Ammount = newTotal, ShareClass = transfer.ShareClass,
                    Date = newDate, Cancelled = False, FromRemainder = True, 
                    Transfer = transfer, CertificateNumber=None)
                if transfer.FromPerson:
                    certificateFrom.ToPerson = transfer.FromPerson
                elif transfer.FromCompany:
                    certificateFrom.ToCompany = transfer.FromCompany

                certificateFrom = updateCertNos(certificateFrom, transfer)
                certificateFrom.save()
                break

#Updates cert numbers and returns cert
def updateCertNos(certificate, transfer):
    certificates = ShareCertificate.objects.filter(ReferenceCompany = transfer.Company,
            ShareClass = transfer.ShareClass).order_by("Date")
    if len(certificates) > 0:
        for index, c in enumerate(certificates):
            if certificate.Date < c.Date:
                certificate.CertificateNumber = c.CertificateNumber
                toUpdateCertNo = certificates[index:len(certificates)]
                for c in toUpdateCertNo:
                    shareClass = transfer.ShareClass
                    number = c.CertificateNumber
                    n = getNextCertificateNumber(shareClass, number=number)
                    c.CertificateNumber = n
                    c.save()
                break
    else:
        n = getNextCertificateNumber(certificate.ShareClass, first=True)
        certificate.CertificateNumber = n

    if certificate.CertificateNumber is None:
        previous = certificates.latest("Date")
        previousNo = previous.CertificateNumber
        n = getNextCertificateNumber(certificate.ShareClass, previousNo)
        certificate.CertificateNumber = n

    return certificate

#given a cert no and share class returns the next number
def getNextCertificateNumber(shareClass, number=False, first=False):
    if first:
        if shareClass.Name.lower() == "common":
            return "1"
        else:
            split = shareClass.Name.split()
            s = split[2][0].upper() + " - " + split[1] + " - " +str(1)
            return str(s)
    else:
        if shareClass.Name.lower() == "common":
            return str(int(number) + 1)
        else:
            split = shareClass.Name.split()
            n = str(int(number.split()[-1]) + 1)
            s = split[2][0].upper() + " - " + split[1] + " - " + n
            return str(s)







def shareholders_ledger(request, company_id=None):
    if request.user.is_authenticated:
        context = {}
        if company_id:
            company = Company.objects.get(pk=company_id)
            context['company'] = company

        transfers = Transfer.objects.filter(Company = company)
        people_ids = []
        for tran in transfers:
            if tran.FromPerson:
                people_ids.append(tran.FromPerson.id)
            if tran.ToPerson:
                people_ids.append(tran.ToPerson.id)
        people = Person.objects.filter(id__in=people_ids)
        peopleClassList = []
        for person in people:
            sharetypes=set()
            for t in transfers:
                if t.FromPerson == person or t.ToPerson == person:
                    sharetypes.add(t.ShareClass)
            d = {'person':person,
                    'shareTypes':sharetypes}
            peopleClassList.append(d)
        company_ids = []
        for tran in transfers:
            if tran.FromCompany and tran.FromCompany != company:
                company_ids.append(tran.FromCompany.id)
            if tran.ToCompany and tran.ToCompany != company:
                company_ids.append(tran.ToCompany.id)
        companies = Company.objects.filter(id__in=company_ids)
        companyClassList = []
        for c in companies:
            sharetypes=set()
            for t in transfers:
                if t.FromCompany == c or t.ToCompany == c:
                    sharetypes.add(t.ShareClass)
            d = {'company':c,
                    'shareTypes':sharetypes}
            companyClassList.append(d)

        mixed2=[]
        for entry in peopleClassList:
            for shareClass in entry['shareTypes']:
                mixed2.append({'type': 'person', 'entity': entry['person'],
                    'shareClass': shareClass})
        for entry in companyClassList:
            for shareClass in entry['shareTypes']:
                mixed2.append({'type': 'company', 'entity': entry['company'],
                    'shareClass': shareClass})

        def compare2(item1, item2):
            item1 = item1['entity'].Name + item1['shareClass'].Name
            item2 = item2['entity'].Name + item2['shareClass'].Name

            if item1 < item2:
                return 1
            elif item1 > item2:
                return -1
            else:
                return 0

        mixed2.sort(key=functools.cmp_to_key(compare2), reverse = True)

        if request.GET.get('query'):
            search_string = request.GET.get('query')
            search_string = search_string.lower()
            to_remove = []
            for entry in mixed2:
                _str = entry['entity'].Name.lower() + " " + entry['shareClass'].Name.lower()
                if search_string not in _str:
                    to_remove.append(entry)
            for entry in to_remove:
                mixed2.remove(entry)

            context['query'] = search_string
        else:
            context['query'] = ""

        context['mixed2'] = mixed2

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(context['mixed2']):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        context['mixed2'] = context['mixed2'][start:end]

        context['page'] = page

        #request for a specific ledger
        if request.GET.get('type'):
            ledgerType = request.GET.get('type')
            context['ledgerType']=ledgerType
            shareClass = request.GET.get('shareClass')
            shareClass = ShareClass.objects.get(pk=shareClass)
            context['shareClass']=shareClass
            if ledgerType == "person":
                p = request.GET.get("id")
                p = Person.objects.get(pk=p)
                context['owner'] = p
                transfers = Transfer.objects.filter(Q(FromPerson \
                    = p, ShareClass=shareClass, Company=company) | Q(ToPerson = p, \
                    ShareClass=shareClass, Company=company)).order_by('Date')
            if ledgerType == "company":
                c = request.GET.get("id")
                c = Company.objects.get(pk=c)
                context['owner'] = c
                transfers = Transfer.objects.filter(Q(FromCompany \
                    = c, ShareClass=shareClass, Company=company) | Q(ToCompany = c, \
                    ShareClass=shareClass, Company=company)).order_by('Date')
            context['t']=[]
            total = 0
            for t in transfers:
                tt={'total':total}
                if t.FromCompany == context['owner'] or t.FromPerson == context['owner']:
                    if t.ToCompany:
                        if t.ToCompany == company:
                            tt['toOrFrom'] = "To - Treasury"
                        else:
                            tt['toOrFrom'] = "To - " + t.ToCompany.__str__()
                    else:
                        tt['toOrFrom'] = "To - " + t.ToPerson.__str__()
                else:
                    if t.FromCompany:
                        if t.FromCompany == company:
                            tt['toOrFrom'] = "From - Treasury"
                        else:
                            tt['toOrFrom'] = "From - " + t.FromCompany.__str__()
                    else:
                        tt['toOrFrom'] = "From - " + t.FromPerson.__str__()

                if t.FromPerson != context['owner'] and t.FromCompany != context['owner']:
                    total += t.Ammount
                    tt['total'] += t.Ammount
                    tt['acquired'] = t.Ammount
                    #Truncate floats that are ints
                    if tt['acquired'].is_integer():
                        tt['acquired'] = int(tt['acquired'])
                    #Format with commas
                    acquired = tt['acquired']
                    acquiredFormatted = f'{acquired:,}'
                    tt['acquired'] = acquiredFormatted
                else:
                    total -= t.Ammount
                    tt['total'] -= t.Ammount
                    tt['transferred'] = t.Ammount
                    #Truncate floats that are ints
                    if tt['transferred'].is_integer():
                        tt['transferred'] = int(tt['transferred'])
                    #Format with commas
                    transferred = tt['transferred']
                    transferredFormatted = f'{transferred:,}'
                    tt['transferred'] = transferredFormatted

                if tt['total'].is_integer():
                    tt['total'] = int(tt['total'])
                
                _total = tt['total']
                totalFormatted = f'{_total:,}'
                tt['totalFormatted'] = totalFormatted
                print(tt['totalFormatted'])

                tt['transfer']=t
                tt['date'] = t.Date.strftime("%Y-%m-%d")
                cert=""
                for c in t.ShareCertificate.all():
                    if c.FromRemainder == True:
                        cert = c
                        break
                    elif c.ToPerson == context['owner']:
                        cert = c
                        break
                    elif c.ToCompany == context['owner']:
                        cert = c
                        break
                tt['cert'] = cert
                context['t'].append(tt)

            #Specific ledger
            return render(request, 'ledger.html', context)
        #Available ledgers
        return render(request, 'shareholders_ledger.html', context)
    else:
        return HttpResponse("Please Login")


def management(request, company_id = None):
    if request.user.is_authenticated:
        context = {}
        company = Company.objects.get(pk=company_id)
        participants = company.Participant.all()
        context['participants'] = participants
        context['company'] = company
        managers = Manager.objects.filter(Company=company,EndDate__isnull=True).order_by("Person")
        context["managers"] = managers
        managers_fixed = []
        for m in context["managers"]:
            m.str = m.__str__()
            managers_fixed.append(m)
        context["managers"] = managers_fixed

        if request.GET.get("type") == "search":
            delete = request.GET.get("delete")
            if delete == "True":
                m = []
                for manager in managers:
                    if request.GET.get("query").lower() in manager.Person.Name.lower():
                        m.append(manager)
                context['managers'] = m
            context['participants'] = []
            for p in participants:
                if p.LinkedPerson:
                    if request.GET.get("query").lower() in p.LinkedPerson.Name.lower():
                        context['participants'].append(p)
        else:
            context['participants'] = []
            for p in participants:
                if p.LinkedPerson:
                    context['participants'].append(p)
        context['participants'].sort(key= lambda x: x.__str__())
        context['managers'].sort(key= lambda x: x.Person.Name)

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if request.GET.get("type") == "search":
            query = request.GET.get("query")
            if delete == "True":
                if end < len(context['managers']):
                    context["hasNextPage"] = True
                else:
                    context["hasNextPage"] = False
                context['managers'] = context['managers'][start:end]
            else:
                if end < len(context['participants']):
                    context["hasNextPage"] = True
                else:
                    context["hasNextPage"] = False
                context['participants'] = context['participants'][start:end]
        else:
            query = ""
            if end < len(context['managers']):
                context["hasNextPageRemove"] = True
            else:
                context["hasNextPageRemove"] = False
            if end < len(context['participants']):
                context["hasNextPageAdd"] = True
            else:
                context["hasNextPageAdd"] = False
            context['participants'] = context['participants'][start:end]
            context['managers'] = context['managers'][start:end]



        context['page'] = page
        context["query"] = query
        if request.GET.get("type") == "search":
            if delete == "True":
                return render(request, "delete_management_search.html", context)
            return render(request, 'enter_management_search.html', context)
        titles = [
                ("Officer", "Officer"),
                ("President", "President"), 
                ("Secretary", "Secretary"),
                ("VP", "VP"),
                ("Other", "Other"),
                ("Director", "Director")
                ]
        _roles = ManagerRole.objects.all()
        context['roles'] = _roles
        if request.method == "POST":
            _type = request.POST.get("type")
            if _type == "delete":
                try:
                    deletedManager = request.POST.get("deletedManager")
                    deletedManager = Manager.objects.get(pk=deletedManager)
                    date = request.POST.get("date")
                    time = request.POST.get("time")
                    dt = date + " " + time
                    date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                    #date = pytz.timezone("America/Halifax").localize(date)
                    deletedManager.EndDate = date
                    deletedManager.save()
                    return HttpResponseRedirect("/companies/" + str(company.id) + \
                        "/changeManagement/?alert=Management%20Updated&alertType=success")
                except Exception as e:
                    error = str(e)
                    return HttpResponseRedirect("/companies/" + str(company.id) + \
                        "/changeManagement/?alert="+error+"&alertType=danger")

            if _type == "add":
                try:
                    date = request.POST.get("date")
                    time = request.POST.get("time")
                    dt = date + " " + time
                    date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                    #date = pytz.timezone("America/Halifax").localize(date)
                    person_id = request.POST.get("person_id")
                    person = Person.objects.get(pk=person_id)
                    role = request.POST.get("role")
                    role = ManagerRole.objects.get(pk=role)
                    existing = Manager.objects.filter(Person=person, Title=role,
                            Company=company)
                    if company.IncorporationDate > date:
                        raise Exception("Company not yet incorporated")
                    if len(existing) > 0 and existing[0].EndDate is None:
                        raise Exception("Manager Already exists")
                    if len(existing) > 0:
                        manager = existing[0]
                        manager.StartDate = date
                        manager.EndDate = None
                        manager.save()
                    else:
                        new_management = Manager(Person=person, Title=role, 
                                Company=company, StartDate=date)
                        new_management.save()

                    return HttpResponseRedirect("/companies/" + str(company.id) + \
                        "/changeManagement/?alert=Management%20Updated&alertType=success")
                except Exception as e:
                    error = str(e)
                    return HttpResponseRedirect("/companies/" + str(company.id) + \
                        "/changeManagement/?alert="+error+"&alertType=danger")
        if request.GET.get("alert"):
            context["alert"] = request.GET.get("alert")
            context["alert_type"] = request.GET.get("alertType")
        return render(request, 'management.html', context)
    else:
        return HttpResponse("Please Login")
    
def registers(request, company_id=None):
    if request.user.is_authenticated:
        context = {}
        company = Company.objects.get(pk=company_id)
        managers = company.Manager.all()
        filled_roles = set([x.Title for x in managers])
        context["roles"] = filled_roles
        transfers = company.Transfer.all()
        if len(transfers) > 0:
            context["hasShareholders"] = True
        else:
            context["hasShareholders"] = False

        try:
            director = ManagerRole.objects.get(Title="Director")
        except:
            director = None
        context["roles"] = []
        if director in filled_roles:
            context["roles"].append(director)
            context["hasDirectors"] = True
            filled_roles.remove(director)
        else:
            context["hasDirectors"] = False
        context["company"] = company
        if len(filled_roles) > 0:
            context["Officer"] = True
            officersList = [m for m in managers if m.Title.Title != "Director"]
            context["Officer"] = True
        else:
            context["Officer"] = False

        if request.GET.get("role"):
            role = request.GET.get("role")
            if role == "Officer":
                context["OfficerSelected"] = True
                context['plural'] = "Officers"
                context['title'] = "Officer"
                officersList.sort(key = lambda x: x.StartDate)
                for m in officersList:
                    m.StartDate = m.StartDate.strftime("%Y-%m-%d")
                    if m.EndDate is not None:
                        m.EndDate = m.EndDate.strftime("%Y-%m-%d")
                context["managers"] = officersList
                return render(request, "managementRegister.html", context)
            if role != "ShareHolder":
                r = ManagerRole.objects.get(pk=role)
                _managers = Manager.objects.filter(Company=company, Title=r).order_by("StartDate")
                if r.Title != "Secretary":
                    plural_name = r.Title+"s"
                else:
                    plural_name = "Secretaries"
                for m in _managers:
                    m.StartDate = m.StartDate.strftime("%Y-%m-%d")
                    if m.EndDate is not None:
                        print("HIT================================")
                        m.EndDate = m.EndDate.strftime("%Y-%m-%d")
                        print(m.EndDate)
                context['managers'] = _managers
                context['plural'] = plural_name
                context['title'] = r.Title
                return render(request, "managementRegister.html", context)

            if role == "ShareHolder":
                context["role"] = "Shareholder's Register"

            transfers = Transfer.objects.filter(Company=company).order_by("Date")

            #creates a dict of form {(entity,ShareClass):[ammount, date]}
            #named entityShareClass
            entities = set()
            for t in transfers:
                entityFrom = t.FromCompany or t.FromPerson
                entityTo = t.ToCompany or t.ToPerson
                entities.add(entityTo)
                entities.add(entityFrom)
            entityShareClass = dict()
            for t in transfers:
                for e in entities:
                    if t.ToPerson == e or t.ToCompany == e:
                        if e != company:
                            entityShareClass[(e,t.ShareClass)]=[0]
            for t in transfers:
                toEntity = t.ToPerson or t.ToCompany
                fromEntity = t.FromPerson or t.FromCompany

                #Keeps running track of entities shares held
                if toEntity != company:
                    entityShareClass[(toEntity, t.ShareClass)][0] += t.Ammount
                if fromEntity != company:
                    entityShareClass[(fromEntity, t.ShareClass)][0] -= t.Ammount

                #Ensures most current date is kept
                if toEntity != company:
                    if len(entityShareClass[(toEntity, t.ShareClass)]) == 1:
                        entityShareClass[(toEntity, t.ShareClass)].append(t.Date)
                    elif t.Date > entityShareClass[(toEntity, t.ShareClass)][1]:
                        entityShareClass[(toEntity, t.ShareClass)][1]=t.Date
                if fromEntity != company:
                    if len(entityShareClass[(fromEntity, t.ShareClass)]) == 1:
                        entityShareClass[(fromEntity, t.ShareClass)].append(t.Date)
                    elif t.Date > entityShareClass[(fromEntity, t.ShareClass)][1]:
                        entityShareClass[(fromEntity, t.ShareClass)][1]=t.Date


            #Delete entities with zero shares held
            to_delete = []
            for key, value in entityShareClass.items():
                if value[0] == 0:
                    to_delete.append(key)
            for key in to_delete:
                del entityShareClass[key]


            #Sort by date
            entityShareClass=dict(sorted(entityShareClass.items(), key = lambda x: x[1][1]))
            #Convert datetime to metric
            for key in entityShareClass:
                entityShareClass[key][1] = \
                    entityShareClass[key][1].strftime("%Y-%m-%d")

            #Truncate decimals if integer
            truncatedDecimalEntityShareClass = {}
            for entry in entityShareClass.items():
                if entry[1][0].is_integer():
                    truncatedDecimalEntityShareClass[entry[0]] = \
                            [int(entry[1][0]), entry[1][1]]
                else:
                    truncatedDecimalEntityShareClass[entry[0]] = \
                            [entry[1][0], entry[1][1]]

            #Format with commas
            formattedTruncatedEntityShareClass = {}
            for entry in truncatedDecimalEntityShareClass.items():
                quantity = entry[1][0]
                quantityFormatted = f'{quantity:,}'
                formattedTruncatedEntityShareClass[entry[0]] = \
                        [quantityFormatted, entry[1][1]]

            context["entities"] = entities
            #context["entityShareClass"] = entityShareClass
            context["entityShareClass"] = formattedTruncatedEntityShareClass
            context["company"] = company

            #Specific register
            return render(request, 'register.html', context)

        #List of available registers
        return render(request, 'registers.html', context)
    else:
        return HttpResponse("Please Login")

def share_class(request):
    if request.user.is_authenticated:

        share_classes = ShareClass.objects.all().order_by("Name")
        context={'share_classes': share_classes}
        context["alert_type"] = None
        context["alert"] = None
        delete = request.GET.get("delete")
        if delete:
            try:
                to_delete = ShareClass.objects.get(pk=delete)
                to_delete.delete()
                return HttpResponseRedirect("/shareClass/?alert=" + \
                            "Share Class Deleted&alertType=success")
            except Exception as e:
                return HttpResponseRedirect("/shareClass/?alert=" + \
                        "ERROR: " + str(e) + "&alertType=danger")
        if request.method == "POST":
            try:
                name = request.POST.get("name")
                existing = ShareClass.objects.filter(Name__iexact=name)
                if len(existing) > 0:
                    raise Exception("Already Exists")
                elif name == "":
                    raise Exception("Cannot be Blank")
                else:
                    share_class = ShareClass(Name=name)
                    share_class.save()
                    return HttpResponseRedirect("/shareClass/?alert=" + \
                            "Share Class Created&alertType=success")
            except Exception as e:
                return HttpResponseRedirect("/shareClass/?alert=" + \
                        "ERROR: " + str(e) + "&alertType=danger")

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(context['share_classes']):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        if request.GET.get("alert"):
            context["alert"] = request.GET.get("alert")
            context["alert_type"] = request.GET.get("alertType")
        context['share_classes'] = context['share_classes'][start:end]

        context['page'] = page
        return render(request, 'share_class.html', context)
    else:
        return HttpResponse("Please Login")

def manager_role(request):
    if request.user.is_authenticated:
        roles = ManagerRole.objects.all()
        context = {'roles': roles}

        delete = request.GET.get("delete")
        if delete:
            try:
                to_delete = ManagerRole.objects.get(pk=delete)
                to_delete.delete()
                context["alert_type"] = "success"
                context["alert"] = "Management Role Deleted"
            except Exception as e:
                context["alert_type"] = "danger"
                context["alert"] = str(e)

        if request.method == "POST":
            try:
                title = request.POST.get("title")
                existing = ManagerRole.objects.filter(Title__iexact=title)
                if title == "":
                    context["alert_type"] = "danger"
                    context["alert"] = "cannot be blank"
                elif len(existing) > 0:
                    context["alert_type"] = "danger"
                    context["alert"] = "Already Exists"
                else:
                    manager_role = ManagerRole(Title=title)
                    manager_role.save()
                    context["alert_type"] = "success"
                    context["alert"] = "Management Role Created"
            except Exception as e:
                context["alert_type"] = "danger"
                context["alert"] = str(e)

        if request.GET.get("page"):
            page = int(request.GET.get("page"))
        else:
            page = 1
        start = (page - 1) * PAGELENGTH
        end = start + PAGELENGTH

        if end < len(context['roles']):
            context["hasNextPage"] = True
        else:
            context["hasNextPage"] = False

        context['roles'] = context['roles'][start:end]

        context['page'] = page

        return render(request, 'manager_role.html', context)
    else:
        return HttpResponse("Please Login")





















