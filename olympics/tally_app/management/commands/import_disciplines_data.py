from django.core.management.base import BaseCommand
from tally_app.models import Country, Athlete, Medal, Event, Discipline


class Command(BaseCommand):
	help = "Import discipline data from a csv file into the database"

	def add_arguments(self, parser):
		parser.add_argument('filepath', type=str, help="Path to the CSV file")

	def handle(self, *args, **options):
		filepath = options['filepath']

		try:
			with open(filepath, 'r') as file:
				file.readline()
				for row in file.readlines():
					sport, discipline, code = row.replace('\n', '').split(',')

					if discipline == '':
						name = sport
					else:
						if discipline in sport:
							name = discipline
						else:
							if sport == 'Aquatics':
								name = discipline
							elif sport in ['Basketball', 'Gymnastics', 'Rowing', 'Volleyball', 'Wrestling', 'Lacrosse', 'Skating', 'Skiing']:
								name = f'{discipline} {sport}'
							else:
								name = f'{sport} {discipline}'

					Discipline.objects.update_or_create(
						code=code,
						defaults={
							'name': name,
							'sport': sport,
						}
					)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {filepath}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{filepath}" not found'))
