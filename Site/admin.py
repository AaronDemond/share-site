from django.contrib import admin
from django.contrib.auth.models import User

from .models import Person, Manager, Company
from .models import ShareClass, AuthorizedShares, Transfer, CompanyParticipant, ManagerRole, ShareCertificate

admin.site.register(Person)
#admin.site.register(User)
admin.site.register(ShareCertificate)
admin.site.register(CompanyParticipant)
admin.site.register(Manager)
admin.site.register(Company)
admin.site.register(ShareClass)
admin.site.register(AuthorizedShares)
admin.site.register(Transfer)
admin.site.register(ManagerRole)




