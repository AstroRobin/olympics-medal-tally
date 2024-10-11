import json
import requests

from django.core.management.base import BaseCommand
from tally_app.models import Country, Athlete, Medal, Event


class Command(BaseCommand):
	help = "Import data from a JSON file into the database"

	def add_arguments(self, parser):
		parser.add_argument('json_file', type=str, help="Path to the JSON file")

	def handle(self, *args, **options):
		json_file_path = options['json_file']

		def handle_user_input(name, iso_code):
			user_input = input(f"Custom flag URL for {name}? (leave blank to pass): ").strip()

			return user_input if user_input else "https://upload.wikimedia.org/wikipedia/commons/2/2f/Missing_flag.png"

		try:
			with open(json_file_path) as file:
				data = json.load(file)

			for item in data:
				print(item.get('ioc_noc_code'))

				flagURL = f"https://raw.githubusercontent.com/hampusborgos/country-flags/main/png250px/{item.get('iso_alpha_2').lower()}.png"
				try:
					response = requests.head(flagURL)
					if response.status_code != 200:
						print(f"No flag found at {flagURL}. Status code: {response.status_code}")
						flagURL = handle_user_input(item.get('country_name'), item.get('iso_alpha_2'))

				except requests.RequestException as e:
					print(f"Error checking flag URL: {e}")
					flagURL = handle_user_input(item.get('country_name'), item.get('iso_alpha_2'))

				if (code := item.get('ioc_noc_code')) is not None:
					Country.objects.update_or_create(
						code=code,
						defaults={
							'fullName': item.get('country_name'),
							'iso': item.get('iso_alpha_2'),
							'flagURL': flagURL,
						}
					)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {json_file_path}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{json_file_path}" not found'))
		except json.JSONDecodeError:
			self.stdout.write(self.style.ERROR(f'Error decoding JSON from file "{json_file_path}"'))