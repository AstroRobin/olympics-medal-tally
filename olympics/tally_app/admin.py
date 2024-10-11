from django.contrib import admin
from tally_app.models import Country, Athlete, Team, Event, Medal, Discipline, Host


class CountryAdmin(admin.ModelAdmin):
	list_display = ['code', 'fullName']


class AthleteAdmin(admin.ModelAdmin):
	list_display = ['id', 'displayName', 'disciplines', 'country']


class TeamAdmin(admin.ModelAdmin):
	list_display = ['codeRaw', 'id', 'discipline', 'country']


class MedalAdmin(admin.ModelAdmin):
	list_display = [
		'rank', 'event', 'object_id', 'content_type', 'content_object'
	]


class DisciplineAdmin(admin.ModelAdmin):
	list_display = ['name', 'sport', 'code']


class EventAdmin(admin.ModelAdmin):
	list_display = ['name', 'discipline', 'gender']


class HostAdmin(admin.ModelAdmin):
	list_display = ['id', 'name', 'season', 'location', 'year', 'startDate', 'endDate']


# Register your models here.
admin.site.register(Country, CountryAdmin)
admin.site.register(Athlete, AthleteAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(Medal, MedalAdmin)
admin.site.register(Host, HostAdmin)
