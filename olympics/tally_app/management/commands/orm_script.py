from django.contrib.contenttypes.models import ContentType
from tally_app.models import Country, Athlete, Team, Event, Medal
from django.db import connection


def run():
	medals = Medal.objects.all()
	for medal in medals:
		print(medal.content_object)