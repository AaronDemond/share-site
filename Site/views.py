from django.http import HttpResponse
import pytz
from django.db.models import Q
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, HttpResponse, HttpResponseRedirect, render_to_response
from Site.models import Company, ShareClass, AuthorizedShares, Person, Transfer, CompanyParticipant, Manager, ManagerRole
from django.urls import resolve

PAGELENGTH = 5

def index(request, **kwargs):

    return render(request, 'index.html', {})

def companies(request, company_id=None, context=None):
    query = request.GET.get('query', None)
    if query:
        ql = Company.objects.filter(Name__icontains=query).order_by("-Modified")
    else:
        ql = Company.objects.all().order_by("-Modified")
    if context:
        context['companies'] = ql
    else:
        context = {'companies' : ql}
    return render(request, 'companies.html', context)
def shareholders_register(request, company_id=None):
    context = {}
    return render(request, 'shareholders_register.html', context)
    
def people(request, context={}):
    query = request.GET.get('query', None)
    ql = []
    if query:
        people = Person.objects.filter(Name__icontains=query).order_by("-pk")
        companies = Company.objects.filter(Name__icontains=query).order_by("-pk")
    else:
        people = Person.objects.all().order_by("-pk")
        companies = Company.objects.all().order_by("-pk")

    for p in people:
        ql.append([p,"person"])
    for c in companies:
        ql.append([c, "company"])
    ql.sort(key=lambda x: x[0].Modified, reverse=True)

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

    return render(request, 'people.html', context)
def link(request, _id=None):
    _type = request.GET.get("type")
    context = {}
    if _type == "person":
        context["entity"] = Person.objects.get(pk=_id)
    elif _type == "company":
        context["entity"] = Company.objects.get(pk=_id)
    if request.GET.get("search"):
        query = request.GET.get("query")
        companies = Company.objects.filter(Name__icontains=query).order_by("-pk")
    else:
        companies = Company.objects.all().order_by("-pk")

    if request.GET.get("company_id"):
        company = Company.objects.get(pk=request.GET.get("company_id"))
        companyReference = company
        companyParticipant = CompanyParticipant(CompanyReference=companyReference)
        if _type == "person":
            companyParticipant.LinkedPerson = context["entity"]
            q = CompanyParticipant.objects.filter(CompanyReference = company,
                    LinkedPerson = context["entity"])
            if len(q) > 0:
                context["alert_type"] = "danger"
                context["alert"] = "Link already exists"
                return people(request, context)

        elif _type == "company":
            companyParticipant.LinkedCompany = context["entity"]
            q = CompanyParticipant.objects.filter(CompanyReference = company,
                    LinkedCompany = context["entity"])
            if len(q) > 0:
                context["alert_type"] = "danger"
                context["alert"] = "Link already exists"
                return people(request, context)
        try:
            companyParticipant.save()
            context["alert_type"] = "success"
            context["alert"] = "Entity Linked"
            return people(request, context)
        except:
            context["alert_type"] = "danger"
            context["alert"] = "Error saving link"
    context["companies"] = companies 
    context["type"] = _type

    return render(request, "link.html", context)

def issue_shares(request, company_id=None):
    current_url = resolve(request.path_info).url_name
    company = Company.objects.get(pk=int(company_id))
    share_classes = ShareClass.objects.all()
    context = {'company' : company}

    #Creates a dict of type {'Share Class' : [Ammount, Document]}
    authorized = company.AuthorizedShares.all()
    share_classes_authorized = {}
    for t in authorized:
        if t.ShareClass not in share_classes_authorized.keys():
            share_classes_authorized[str(t.ShareClass)] = [0]
    for t in authorized:
        share_classes_authorized[str(t.ShareClass)][0] += t.Ammount
        if t.Document:
            share_classes_authorized[str(t.ShareClass)].append(t.Document)
    transfers = Transfer.objects.filter(Company=company, ToCompany=company)
    for t in transfers:
        if len(share_classes_authorized)>0:
            share_classes_authorized[str(t.ShareClass)][0] -= t.Ammount
    context['share_classes'] = share_classes
    context['share_classes_authorized'] = share_classes_authorized

    #Either a share issue request or a file upload
    if request.method == "POST":
        #File upload linked to a share class
        if request.POST.get("append") == "True":
            _file = request.FILES["appendedFile"]
            share_class = request.POST.get("ShareClass")
            share_class = ShareClass.objects.get(pk=share_class)
            authorized_shares = AuthorizedShares.objects.filter(ShareClass=share_class)
            #remove previous documents
            for a in authorized_shares:
                if a.Document is not None:
                    a.Document = None
                    a.save()
            #add new document
            authorized_shares_obj = authorized_shares[0]
            authorized_shares_obj.Document = _file
            authorized_shares_obj.save()
            context["error_type"] = "success"
            context["alert"] = "Document Appended"
            return companies(request=request,context=context)

        #Authorize shares request
        share_class = request.POST.get('ShareClass')
        ammount = request.POST.get('Ammount')
        date = request.POST.get("date")
        time = request.POST.get("time")
        value = request.POST.get("parValue")
        dt = date + " " + time
        print(dt)
        if len(request.FILES) != 0:
            _file = request.FILES["uploadedFile"]
        else:
            _file = False
        

        if share_class and ammount and date and time:
            if int(ammount) < 0:
                context["error_type"] = "danger"
                context["alert"] = "ERROR! Cannot issue negative share"
                return render(request, 'issue_shares.html', context)

            try:
                share_class = ShareClass.objects.get(pk=share_class)
                date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                if _file:
                    authorized_shares = AuthorizedShares(Company=company,
                            Ammount=ammount, ShareClass=share_class,
                            Date=date, Value=value, Document=_file)
                else:
                    authorized_shares = AuthorizedShares(Company=company,
                            Ammount=ammount, ShareClass=share_class,
                            Date=date, Value=value)
                authorized_shares.save()
                context["error_type"] = "success"
                context["alert"] = "Shares authorized"

                return companies(request=request,context=context)
            except Exception as e:
                context["error_type"] = "danger"
                context["alert"] = "ERROR! " + str(e)
        else:
            context["error_type"] = "danger"
            context["alert"] = "ERROR! Please fill the entire form"

    return render(request, 'issue_shares.html', context)

def create_company(request):
    context = {}
    if request.method == "POST":
        name = request.POST.get("Name")
        date = datetime.datetime.now()
        try:
            new_company = Company(Name=name, Modified=date)
            new_company.save()
            context["alert_type"] = "success"
            context["alert"] = "Company created"
            return people(request=request, context = context)
        except Exception as e:
            context["alert_type"] = "danger"
            context["alert"] = "ERROR! " + str(e)

    return render(request, 'create_company.html', context)

def create_person(request):
    context = {}
    if request.method == "POST":
        try:
            name = request.POST.get("Name")
            address = request.POST.get("Address")
            date = datetime.datetime.now()
            new_person = Person(Name = name, Address = address, Modified = date)
            new_person.save()
            context["alert_type"] = "success"
            context["alert"] = "Person created"
            return people(request=request, context = context)
        except Exception as e:
            context["alert_type"] = "danger"
            context["alert"] = "ERROR! " + str(e)
            return people(request=request, context = context)
    return render(request, 'create_person.html', context)

def transfers(request, company_id=None, transfer_id=None,context={}):
    company = Company.objects.get(pk=company_id)
    _transfers = list(Transfer.objects.filter(Company=company).order_by("-Date"))
    context["transfers"] = _transfers
    context["company"] = company
    tt=[]
    if transfer_id:
        transfer = Transfer.objects.get(pk=transfer_id)
        context["transfer"] = transfer
        context["date"] = transfer.Date.date()
        context["from"] = transfer.FromCompany or transfer.FromPerson
        context["to"] = transfer.ToPerson or transfer.ToCompany
        auth_shares = AuthorizedShares.objects.filter(Company=company)
        auth_types = set([x.ShareClass for x in auth_shares])
        auth_types_value = {}

        #Returns a dict of type {(ShareClass,Value):Ammount)}
        for a in auth_types:
            auth_types_value[a] = set()
        for a in auth_shares:
            auth_types_value[a.ShareClass].add(a.Value)
        auth_totals = {}
        print(auth_types_value)
        for a in auth_types:
            for value in auth_types_value[a]:
                auth_totals[(a,value)] = 0
                for auth in auth_shares:
                    if auth.ShareClass == a and auth.Value == value:
                        auth_totals[(a,value)] += auth.Ammount

        #Removes bought back shares from the dict created above
        for auth_type in auth_types:
            all_tran = Transfer.objects.filter(Company=company,
                    ShareClass=auth_type,ToCompany=company)
            all_auth = AuthorizedShares.objects.filter(Company=company,
                    ShareClass=auth_type)
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

        context["no_of_auth_types"] = len(auth_totals)
        context["auth_totals"] = auth_totals 
        return render(request, 'certificate.html', context)
    if request.GET.get("query"):
        query = request.GET.get("query").lower()
        for t in _transfers:
            if query in t.__str__().lower():
                tt.append(t)
        context['transfers'] = tt

    #User confirmed deletion of impossible transfers
    if request.POST.get("confirm"):
        try:
            selected = request.POST.getlist("confirm")
            to_delete = Transfer.objects.filter(pk__in=selected)
            context['error_type'] = "success"
            context['alert'] = "Transfers deleted"
            to_delete.delete()
        except Exception as e:
            context['error_type'] = "danger"
            context['alert'] = "Problem deleting transfers: " + str(e)

        return companies(request, context = context)

    #Get list of impossible transfers
    if request.POST.get("selectedTransfer"):
        transfer_id = request.POST.get("selectedTransfer")
        share_type_id = request.POST.get("selectedShareType")
        shareClass = ShareClass.objects.get(pk=share_type_id) 
        _transfers = list(Transfer.objects.filter(Company=company, ShareClass=shareClass).order_by("Date"))
        transfer = Transfer.objects.get(pk=transfer_id)
        _transfers.remove(transfer)
        to_be_deleted = []
        to_be_deleted.append(transfer)
        participants = company.Participant.all()
        register = {}
        for p in participants:
            if p.LinkedPerson:
                register[p.LinkedPerson] = 0
            if p.LinkedCompany:
                register[p.LinkedCompany] = 0
        auth_shares = AuthorizedShares.objects.filter(Company=company, ShareClass=shareClass)
        auth_ammount = sum([x.Ammount for x in auth_shares])
        register[company] = auth_ammount

        for t in _transfers:
            receiver = t.ToPerson or t.ToCompany
            sender = t.FromPerson or t.FromCompany
            if register[sender] >= t.Ammount:
                register[sender] -= t.Ammount
                if receiver != company:
                    register[receiver] += t.Ammount
                else:
                    register[receiver] -= t.Ammount
            else:
                to_be_deleted.append(t)
        context["transfers"] = to_be_deleted
        return render(request, 'transfers_confirm.html', context)

    return render(request, 'transfers.html', context)
import functools
def enter_transfer(request, company_id=None):
    company = Company.objects.get(pk=int(company_id))
    participants = company.Participant.all()
    share_classes = ShareClass.objects.all()
    context = {}
    context['company']=company
    context['share_classes']=share_classes
    def compare(item1, item2):
        item1 = item1.LinkedPerson or item1.LinkedCompany
        item2 = item2.LinkedPerson or item2.LinkedCompany
        if item1.Modified < item2.Modified:
            return -1
        elif item1.Modified > item2.Modified:
            return 1
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

        date = request.POST.get("date")
        time = request.POST.get("time")
        dt = date + " " + time
        date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
        date = pytz.timezone("America/Halifax").localize(date)
        price = request.POST.get("price")
        ammount = request.POST.get("ammount")
        shareClass = request.POST.get("shareClass")
        shareClass = ShareClass.objects.get(pk=shareClass)

        transfer = Transfer(Date=date,Price=price,Ammount=ammount,
                Company=company,ShareClass=shareClass)

        fromCompany = request.POST.get("fromCompany")
        fromPerson = request.POST.get("fromPerson")
        toPerson = request.POST.get("toPerson")
        toCompany = request.POST.get("toCompany")
        if fromCompany and toCompany:
            if fromCompany == toCompany:
                context['error_type'] = "danger"
                context['alert'] = "Origin same as destination"
                return companies(request, context=context)
        if fromPerson and toPerson:
            if fromPerson == toPerson:
                context['error_type'] = "danger"
                context['alert'] = "Origin same as destination"
                return companies(request, context=context)
        if fromPerson:
            fromPerson = Person.objects.get(pk=fromPerson)
            transfer.FromPerson = fromPerson
        elif fromCompany:
            fromCompany = Company.objects.get(pk=fromCompany)
            transfer.FromCompany = fromCompany
        else:
            context['error_type'] = "danger"
            context['alert'] = "Select an origin"
            return companies(request, context=context)
        if toPerson:
            toPerson = Person.objects.get(pk=toPerson)
            transfer.ToPerson = toPerson
        elif toCompany:
            toCompany = Company.objects.get(pk=toCompany)
            transfer.ToCompany = toCompany
        else:
            context['error_type'] = "danger"
            context['alert'] = "Select a destination"
            return companies(request, context=context)

        def checkEnoughShares(t):
            if t == "person":
                print(fromPerson)
                transfers = Transfer.objects.filter(Q(FromPerson \
                = fromPerson, ShareClass=shareClass) |\
                Q(ToPerson = fromPerson, ShareClass=shareClass)).order_by('Date')
                transfers = list(transfers)
                total = 0
                newInserted = False
                for t in transfers:
                    if t.Date > date and newInserted == False:
                        total -= int(ammount)
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
                    total -= int(ammount)
                    if total < 0:
                        return False
                return True

            if t == "company":
                if company == fromCompany:
                    auth_shares = AuthorizedShares.objects.filter(Company=company,
                            ShareClass=shareClass)
                    total = 0
                    transfers = Transfer.objects.filter(Q(FromCompany \
                    = company, ShareClass=shareClass, Company=company) | \
                    Q(ToCompany = company, ShareClass=shareClass, Company=company)).order_by('Date')
                    all_tran = []
                    all_tran.extend(list(transfers))
                    all_tran.extend(list(auth_shares))
                    transfers = list(transfers)
                    all_tran.sort(key = lambda x: x.Date)
                    newInserted = False
                    for t in all_tran:
                        if t.Date > date and newInserted == False:
                            total -= int(ammount)
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
                        total -= int(ammount)
                        if total < 0:
                            return False
                    return True
                else:
                    transfers = Transfer.objects.filter(Q(FromCompany \
                    = fromCompany, ShareClass=shareClass) |\
                    Q(ToCompany = fromCompany, ShareClass=shareClass)).order_by('Date')
                    total = 0
                    newInserted = False
                    for t in transfers:
                        if t.Date > date and newInserted == False:
                            total -= int(ammount)
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
                        total -= int(ammount)
                        if total < 0:
                            return False
                    return True

        if fromCompany:
            enough = checkEnoughShares("company")
        elif fromPerson:
            enough = checkEnoughShares("person")
        if enough:
            transfer.save()
            context['error_type'] = "success"
            context['alert'] = "Transver Saved"
        else:
            context['error_type'] = "danger"
            context['alert'] = "Not enough shares!"
        return companies(request, context=context)


    return render(request, 'enter_transfer.html', context)




def shareholders_ledger(request, company_id=None):
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
    context['peopleClassList']=peopleClassList
    context['companyClassList']=companyClassList
    mixed = []
    for entry in peopleClassList:
        mixed.append({'type': 'person', 'entity': entry['person'], 'shareTypes': entry['shareTypes']})
    for entry in companyClassList:
        mixed.append({'type': 'company', 'entity': entry['company'], 'shareTypes': entry['shareTypes']})
    mixed.sort(key = lambda x: x['entity'].Modified, reverse = True)
    context['mixed'] = mixed
    if request.GET.get('query'):
        search_string = request.GET.get('query')
        search_string = search_string.lower()
        for p in context['peopleClassList']:
            if search_string not in p['person'].Name.lower():
                context['peopleClassList'].remove(p)
        for p in context['companyClassList']:
            if search_string not in p['company'].Name.lower():
                context['companyClassList'].remove(p)
        return render(request, 'ledger_ajax.html', context)

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
                = p, ShareClass=shareClass) | Q(ToPerson = p, \
                ShareClass=shareClass)).order_by('Date')
        if ledgerType == "company":
            c = request.GET.get("id")
            c = Company.objects.get(pk=c)
            context['owner'] = c
            transfers = Transfer.objects.filter(Q(FromCompany \
                = c, ShareClass=shareClass) | Q(ToCompany = c, \
                ShareClass=shareClass)).order_by('Date')
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
            else:
                total -= t.Ammount
                tt['total'] -= t.Ammount
                tt['transferred'] = t.Ammount
            tt['transfer']=t
            context['t'].append(tt)

        return render(request, 'ledger.html', context)
    print("HIT")
    return render(request, 'shareholders_ledger.html', context)


def management(request, company_id = None):
    context = {}
    company = Company.objects.get(pk=company_id)
    participants = company.Participant.all()
    context['participants'] = participants
    context['company'] = company
    managers = Manager.objects.filter(Company=company,EndDate__isnull=True)
    context["managers"] = managers
    if request.GET.get("type") == "search":
        delete = request.GET.get("delete")
        if delete == "True":
            m = []
            for manager in managers:
                if request.GET.get("query").lower() in manager.Person.Name.lower():
                    m.append(manager)
            context['managers'] = m
            return render(request, "delete_management_search.html", context)
        print(request.GET.get("query"))
        context['participants'] = []
        for p in participants:
            if p.LinkedPerson:
                if request.GET.get("query") in p.LinkedPerson.Name.lower():
                    context['participants'].append(p)
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
                deletedManager.EndDate = date
                deletedManager.save()
                context["error_type"] = "success"
                context["alert"] = "Management updated"
            except Exception as e:
                context["error_type"] = "danger"
                context["alert"] = str(e)

            return companies(request, context = context)

        if _type == "add":
            try:
                date = request.POST.get("date")
                time = request.POST.get("time")
                dt = date + " " + time
                date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M:%S")
                person_id = request.POST.get("person_id")
                print(person_id)
                person = Person.objects.get(pk=person_id)
                role = request.POST.get("role")
                role = ManagerRole.objects.get(pk=role)
                existing = Manager.objects.filter(Person=person, Title=role,
                        Company=company)
                if len(existing) > 0:
                    context["error_type"] = "danger"
                    context["alert"] = "Already exists"
                    return companies(request, context = context)
                new_management = Manager(Person=person, Title=role, Company=company, StartDate=date)
                new_management.save()

                context["error_type"] = "success"
                context["alert"] = "Management updated"
            except Exception as e:
                context["error_type"] = "danger"
                context["alert"] = str(e)
            return companies(request, context = context)
    return render(request, 'management.html', context)
    
def registers(request, company_id=None):
    company = Company.objects.get(pk=company_id)
    managers = company.Manager.filter(EndDate__isnull=True)
    filled_roles = set([x.Title for x in managers])
    context = {'roles' : filled_roles, 'company' : company}
    if request.GET.get("role"):
        role = request.GET.get("role")
        if role != "ShareHolder":
            context["role"] = ManagerRole.objects.get(pk=role).__str__() + "s" + " Register"
        if role == "Secretary":
            context["role"] = "Secretaries Register"

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

        #Convert datetime to date
        for key in entityShareClass:
            entityShareClass[key][1] = entityShareClass[key][1].date()

        #Delete entities with zero shares held
        to_delete = []
        for key, value in entityShareClass.items():
            if value[0] == 0:
                to_delete.append(key)
        for key in to_delete:
            del entityShareClass[key]

        #Remove all entities who are not part of selected management
        if role != "ShareHolder":
            role = ManagerRole.objects.get(pk=role)
            filteredManagers = company.Manager.filter(EndDate__isnull = True, Title=role)
            entities = set()
            for manager in filteredManagers:
                entities.add(manager.Person)
            to_delete = []
            for key, value in entityShareClass.items():
                if key[0] not in entities:
                    to_delete.append(key)
            for key in to_delete:
                del entityShareClass[key]

        #Sort by date
        print(entityShareClass)
        entityShareClass=dict(sorted(entityShareClass.items(), key = lambda x: x[1][1]))
        print("+++++++++++++++++++++++++++++")
        print(entityShareClass)

        context["entities"] = entities
        context["entityShareClass"] = entityShareClass
        context["company"] = company
        return render(request, 'register.html', context)
    return render(request, 'registers.html', context)

def share_class(request):
    share_classes = ShareClass.objects.all()
    context={'share_classes': share_classes}
    delete = request.GET.get("delete")
    if delete:
        try:
            to_delete = ShareClass.objects.get(pk=delete)
            to_delete.delete()
            context["alert_type"] = "success"
            context["alert"] = "Share Class Deleted"
            return render(request, 'share_class.html', context)
        except Exception as e:
            context["alert_type"] = "danger"
            context["alert"] = str(e)
            return render(request, 'share_class.html', context)
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            existing = ShareClass.objects.filter(Name=name)
            if len(existing) > 0:
                context["alert_type"] = "danger"
                context["alert"] = "Already Exists"
                return render(request, 'share_class.html', context)

            share_class = ShareClass(Name=name)
            share_class.save()
            context["alert_type"] = "success"
            context["alert"] = "Share class created"
        except Exception as e:
            context["alert_type"] = "danger"
            context["alert"] = str(e)
    return render(request, 'share_class.html', context)

def manager_role(request):
    roles = ManagerRole.objects.all()
    context = {'roles': roles}

    delete = request.GET.get("delete")
    if delete:
        try:
            to_delete = ManagerRole.objects.get(pk=delete)
            to_delete.delete()
            context["alert_type"] = "success"
            context["alert"] = "Managment Role Deleted"
            return render(request, 'manager_role.html', context)
        except Exception as e:
            context["alert_type"] = "danger"
            context["alert"] = str(e)
            return render(request, 'manager_role.html', context)

    if request.method == "POST":
        try:
            title = request.POST.get("title")
            existing = ManagerRole.objects.filter(Title=title)
            if len(existing) > 0:
                context["alert_type"] = "danger"
                context["alert"] = "Already Exists"
                return render(request, 'manager_role.html', context)

            manager_role = ManagerRole(Title=title)
            manager_role.save()
            context["alert_type"] = "success"
            context["alert"] = "Management Role Created"
        except Exception as e:
            context["alert_type"] = "danger"
            context["alert"] = str(e)

    return render(request, 'manager_role.html', context)





















