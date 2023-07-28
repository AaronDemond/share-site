from django.contrib import admin

from .models import Person, Manager, Company
from .models import ShareClass, AuthorizedShares, Transfer, CompanyParticipant

admin.site.register(Person)
admin.site.register(CompanyParticipant)
admin.site.register(Manager)
admin.site.register(Company)
admin.site.register(ShareClass)
admin.site.register(AuthorizedShares)
admin.site.register(Transfer)




