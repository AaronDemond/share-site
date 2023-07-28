from django.http import HttpResponse
from django.db.models import Q
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, HttpResponse, HttpResponseRedirect, render_to_response
from Site.models import Company, ShareClass, AuthorizedShares, Person, Transfer, CompanyParticipant
from django.urls import resolve


def index(request, **kwargs):

    return render(request, 'index.html', {})

def companies(request, company_id=None, context=None):
    query = request.GET.get('query', None)
    if query:
        ql = Company.objects.filter(Name__icontains=query).order_by("-pk")
    else:
        ql = Company.objects.all().order_by("-pk")
    if context:
        context['companies'] = ql
    else:
        context = {'companies' : ql}
    return render(request, 'companies.html', context)
def shareholders_register(request, company_id=None):
    context = {}
    return render(request, 'shareholders_register.html', context)
    
def people(request, context=None):
    query = request.GET.get('query', None)
    if query:
        ql = Person.objects.filter(Name__icontains=query).order_by("-pk")
    else:
        ql = Person.objects.all().order_by("-pk")
    if context:
        context['people'] = ql
    else:
        context = {'people' : ql,}
    return render(request, 'people.html', context)

def issue_shares(request, company_id=None):
    current_url = resolve(request.path_info).url_name
    #print(reoquest.path)
    print("referer:")
    print(request.META)
    print(current_url)
    company = Company.objects.get(pk=int(company_id))
    share_classes = ShareClass.objects.all()
    context = {'company' : company}


    authorized = company.AuthorizedShares.all()
    share_classes_authorized = {}
    for t in authorized:
        if t.ShareClass not in share_classes_authorized.keys():
            share_classes_authorized[str(t.ShareClass)] = 0
    for t in authorized:
        share_classes_authorized[str(t.ShareClass)] += t.Ammount


    context['share_classes'] = share_classes
    context['share_classes_authorized'] = share_classes_authorized

    if request.method == "POST":
        share_class = request.POST.get('ShareClass')
        ammount = request.POST.get('Ammount')
        date = request.POST.get("date")
        time = request.POST.get("time")
        dt = date + " " + time
        

        if share_class and ammount and date and time:
            if int(ammount) < 0:
                context["error_type"] = "danger"
                context["alert"] = "ERROR! Cannot issue negative share"
                return render(request, 'issue_shares.html', context)

            try:
                date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M")
                share_class = ShareClass.objects.get(pk=share_class)

                authorized_shares = AuthorizedShares(Company=company,
                        Ammount=ammount, ShareClass=share_class,
                        Date=date)
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
        try:
            new_company = Company(Name=name)
            new_company.save()
            context["error_type"] = "success"
            context["alert"] = "Company created"
            return companies(request=request, context = context)
        except Exception as e:
            context["error_type"] = "danger"
            context["alert"] = "ERROR! " + str(e)

    return render(request, 'create_company.html', context)

def enter_transfer(request, company_id=None):
    company = Company.objects.get(pk=int(company_id))
    participants = company.Participant.all()
    share_classes = ShareClass.objects.all()
    context = {}
    context['company']=company
    context['share_classes']=share_classes
    context['participants']=participants
    if request.GET.get('type') == 'search':
        context['participants'] = []
        query = request.GET.get('query')
        for p in participants:
            if p.LinkedPerson:
                if query in p.LinkedPerson.Name.lower():
                    context['participants'].append(p)
            elif p.LinkedCompany:
                if query in p.LinkedCompany.Name.lower():
                    context['participants'].append(p)
        return render(request, 'enter_transfer_search.html', context)
    if request.method=="POST":

        date = request.POST.get("date")
        time = request.POST.get("time")
        dt = date + " " + time
        date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M")
        price = request.POST.get("price")
        ammount = request.POST.get("ammount")
        shareClass = request.POST.get("shareClass")
        shareClass = ShareClass.objects.get(pk=shareClass)

        transfer = Transfer(Date=date,Price=price,Ammount=ammount,
                Company=company,ShareClass=shareClass)

        fromPerson = request.POST.get("fromPerson")
        if fromPerson:
            fromPerson = Person.objects.get(pk=fromPerson)
            transfer.FromPerson = fromPerson
        fromCompany = request.POST.get("fromCompany")
        if fromCompany:
            fromCompany = Company.objects.get(pk=fromCompany)
            transfer.FromCompany = fromCompany
        toPerson = request.POST.get("toPerson")
        if toPerson:
            toPerson = Person.objects.get(pk=toPerson)
            transfer.ToPerson = toPerson
        toCompany = request.POST.get("toCompany")
        if toCompany:
            toCompany = Company.objects.get(pk=toCompany)
            transfer.ToCompany = toCompany

        def checkEnoughShares(t):
            if t == "person":
                print(fromPerson)
                transfers_rec = Transfer.objects.filter(ToPerson=fromPerson,
                        Date__lt=date,
                        ShareClass=shareClass, Company=company)
                total = 0
                for tran in transfers_rec:
                    total += tran.Ammount

                transfers_sent = Transfer.objects.filter(FromPerson=fromPerson,
                        ShareClass=shareClass,
                        Date__lte=date,
                        Company=company)
                for tran in transfers_sent:
                    total -= tran.Ammount

                print(total)
                if total >= int(ammount):
                    return True
                else:
                    return False
            if t == "company":
                if company == toCompany:
                    auth_shares = AuthorizedShares.objects.filter(Company=fromCompany,
                            ShareClass=shareClass)
                    total = 0
                    for tran in auth_shares:
                        total += tran.Ammount
                    auth_deleted = Transfer.objects.filter(ToCompany=toCompany,
                            ShareClass=shareClass, Company=company)
                    for tran in auth_deleted:
                        total -= tran.Ammount
                    if total >= int(ammount):
                        return True
                    else:
                        return False
                else:
                    transfers_rec = Transfer.objects.filter(ToPerson=fromPerson,
                            Date__lt=date,
                            ShareClass=shareClass, Company=company)
                    total = 0
                    for tran in transfers_rec:
                        total += tran.Ammount

                    transfers_sent = Transfer.objects.filter(FromPerson=fromPerson,
                            ShareClass=shareClass,
                            Date__lte=date,
                            Company=company)
                    for tran in transfers_sent:
                        total -= tran.Ammount

                    print(total)
                    if total >= int(ammount):
                        return True
                    else:
                        return False

        if fromCompany:
            enough = checkEnoughShares("company")
        elif fromPerson:
            enough = checkEnoughShares("company")
        if enough:
            transfer.save()
            context['error_type'] = "success"
            context['alert'] = "Transver Saved"
        else:
            context['error_type'] = "danger"
            context['alert'] = "Not enough shares!"
        return companies(request, context=context)


    return render(request, 'enter_transfer.html', context)

def enter_transfer_person(request, person_id=None):

    person = Person.objects.get(pk=int(person_id))
    share_classes = ShareClass.objects.all()
    companies = Company.objects.all().order_by("-pk")

    context = {'person':person, 
            'share_classes' : share_classes,
            'companies' : companies}

    if request.method == "POST":
        date = request.POST.get("date")
        time = request.POST.get("time")
        dt = date + " " + time

        
        fromPerson = request.POST.get("fromPerson")
        toPerson = request.POST.get("toPerson")
        fromCompany = request.POST.get("fromCompany")
        toCompany = request.POST.get("toCompany")
        shareClass = request.POST.get("shareClass")
        price = request.POST.get("price")
        ammount = request.POST.get("ammount")
        company = request.POST.get("company")

        try:
            #date = datetime.datetime.strptime(date, '%Y-%m-%d')
            date = datetime.datetime.strptime(dt,"%Y-%m-%d %H:%M")
            shareClass = ShareClass.objects.get(pk=shareClass)
            company = Company.objects.get(pk=company)

            transfer = Transfer(Date = date,
                    ShareClass = shareClass,
                    Price = price,
                    Ammount = ammount,
                    Company = company)
        except:
            context['alert'] = "Fill in all fields correctly"
            context['alert_type'] = "danger"
            return people(request,context=context)



        def checkEnoughShares(t):
            if t == "person":
                print(fromPerson)
                transfers_rec = Transfer.objects.filter(ToPerson=fromPerson,
                        Date__lt=date,
                        ShareClass=shareClass, Company=company)
                total = 0
                for tran in transfers_rec:
                    total += tran.Ammount

                transfers_sent = Transfer.objects.filter(FromPerson=fromPerson,
                        ShareClass=shareClass,
                        Date__lte=date,
                        Company=company)
                for tran in transfers_sent:
                    total -= tran.Ammount

                print(total)
                if total >= int(ammount):
                    return True
                else:
                    return False
            if t == "company":
                auth_shares = AuthorizedShares.objects.filter(Company=fromCompany,
                        ShareClass=shareClass)
                total = 0
                for tran in auth_shares:
                    total += tran.Ammount
                auth_deleted = Transfer.objects.filter(ToCompany=toCompany,
                        ShareClass=shareClass, Company=company)
                for tran in auth_deleted:
                    total -= tran.Ammount
                if total >= int(ammount):
                    return True
                else:
                    return False


        if fromPerson:
            fromPerson = Person.objects.get(pk=fromPerson)
            if checkEnoughShares(t="person"):
                transfer.FromPerson = fromPerson
            else:
                context['alert'] = "Person does not have enough shares!"
                context['alert_type'] = "danger"
                return people(request,context=context)
        if toPerson:
            toPerson = Person.objects.get(pk=toPerson)
            transfer.ToPerson = toPerson
        if fromCompany:
            fromCompany = Company.objects.get(pk=fromCompany)
            if checkEnoughShares(t="company"):
                if fromCompany == company:
                    transfer.FromCompany = fromCompany
                else:
                    context['alert'] = "Companies must match"
                    context['alert_type'] = "danger"
                    return people(request,context=context)
            else:
                context['alert'] = "Company does not have enough shares!"
                context['alert_type'] = "danger"
                return people(request,context=context)
        if toCompany:
            toCompany = Company.objects.get(pk=toCompany)
            transfer.ToCompany = toCompany

        try:
            transfer.save()
            alert="Transfer saved."
            alert_type = "success"
        except:
            alert="Transfer not saved"
            alert_type = "danger"

        
    if request.method=="POST":
        context['alert'] = alert
        context['alert_type'] = alert_type
        return people(request,context=context)

    return render(request, 'enter_transfer_person.html', context)

@csrf_exempt
def fromCompany(request):
    query = request.GET.get('query', None)
    if query:
        ql = Company.objects.filter(Name__icontains=query).order_by("-pk")
    else:
        ql = Company.objects.all().order_by("-pk")
    direction = request.GET.get('direction', None)
    context = {'companies' : ql, 'direction':direction}
    t = request.GET.get('type')
    if t:
        return render(request, 'companies_ajax_2.html', context)
    return render(request, 'companies_ajax.html', context)
    return HttpResponse("TEST")

@csrf_exempt
def companiesAjax(request):
    query = request.GET.get('query', None)
    if query:
        ql = Company.objects.filter(Name__icontains=query).order_by("-pk")
    else:
        ql = Company.objects.all().order_by("-pk")
    context = {'companies' : ql}
    return render(request, 'companies_ajax.html', context)

@csrf_exempt
def personSearch(request):
    query = request.GET.get('query', None)
    if query:
        ql = Person.objects.filter(Name__icontains=query).order_by("-pk")
    else:
        ql = Person.objects.all().order_by("-pk")
    direction = request.GET.get('direction', None)
    _type = request.GET.get('type', None)
    company_id = request.GET.get('company_id',None)
    context = {'people' : ql, 'direction':direction}
    if _type:

        company = Company.objects.get(pk=company_id)
        transfers = Transfer.objects.filter(Company = company)
        ids = []
        for tran in transfers:
            if tran.FromPerson:
                ids.append(tran.FromPerson.id)
            if tran.ToPerson:
                ids.append(tran.ToPerson.id)
        people = Person.objects.filter(id__in=ids)
        shareDictList={}
        for person in people:
            sharetypes=set()
            for t in transfers:
                if t.FromPerson == person or t.ToPerson == person:
                    sharetypes.add(t.ShareClass)
            shareDictList[person.id]=sharetypes
        context['shareDictList']=shareDictList
        return render(request, 'people_ajax_ledger.html', context)
    return render(request, 'people_ajax.html', context)
def shareholders_ledger_new(request, company_id=None):
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
        if tran.FromCompany:
            if tran.FromCompany != company:
                company_ids.append(tran.FromCompany.id)
        if tran.ToCompany:
            if tran.FromCompany != company:
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
    return render(request, 'shareholders_ledger.html', context)

def shareholders_ledger(request, company_id=None, 
        person_id=None,share_class_id=None):
    print(share_class_id)
    context = {}
    company = Company.objects.get(pk=company_id)
    if share_class_id:
        shareClass = ShareClass.objects.get(pk=share_class_id)
    transfers = Transfer.objects.filter(Company = company)
    ids = []
    for tran in transfers:
        if tran.FromPerson:
            ids.append(tran.FromPerson.id)
        if tran.ToPerson:
            ids.append(tran.ToPerson.id)
    people = Person.objects.filter(id__in=ids)
    shareDictList={}
    for person in people:
        sharetypes=set()
        for t in transfers:
            if t.FromPerson == person or t.ToPerson == person:
                sharetypes.add(t.ShareClass)
        shareDictList[person.id]=sharetypes
    context['shareDictList']=shareDictList




    context['people']=people
    context['company']=company
    if person_id:
        person = Person.objects.get(pk=person_id)
        person_transfers = Transfer.objects.filter(Q(FromPerson \
                = person, ShareClass=shareClass) | Q(ToPerson = person, ShareClass=shareClass)).order_by('Date')
        pt = []
        total = 0
        context['t']=[]
        for t in person_transfers:
            tt={'total':total}
            if t.FromCompany:
                tt['toOrFrom'] = "From - Treasury"
            elif t.ToCompany:
                tt['toOrFrom'] = "To - Treasury"
            elif t.ToPerson == person:
                tt['toOrFrom'] = "From - " + t.FromPerson.__str__()
            else:
                tt['toOrFrom'] = "To - " + t.ToPerson.__str__()


            if t.FromPerson != person or t.FromCompany:
                total += t.Ammount
                tt['total'] += t.Ammount
            else:
                total -= t.Ammount
                tt['total'] -= t.Ammount
            if t.ToPerson == person:
                tt['acquired'] = t.Ammount
            else:
                tt['transferred'] = t.Ammount
            tt['transfer']=t
            context['t'].append(tt)

        context['shareClass']=shareClass
        context['person']=person
        context['person_transfers']=person_transfers
        context['pt']=pt
        return render(request, 'person_ledger.html', context)

    return render(request, 'shareholders_ledger.html', context)

    




















