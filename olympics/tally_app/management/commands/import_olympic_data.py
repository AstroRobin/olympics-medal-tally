import os
from pathlib import Path
from zipfile import ZipFile
import csv
import requests
from datetime import date

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.contrib.contenttypes.models import ContentType
from kaggle.api.kaggle_api_extended import KaggleApi

from tally_app.models import Country, Athlete, Team, Medal, Event, Discipline, Host
from tally_app.utils import fetch_medals_data


class Command(BaseCommand):
	help = 'Update medals data from Kaggle API'

	def add_arguments(self, parser):
		parser.add_argument('dataset', type=str,
			help='The Kaggle dataset indentifier.')
		parser.add_argument('filename', type=str,
			help='The file name within the dataset')

	def handle(self, *args, **options):
		dataset = options['dataset']
		filename = options['filename']
		downloadPath = Path('data/paris_2024_olympic_summer_games')
		filePath = downloadPath / filename

		# Initialize Kaggle API
		api = KaggleApi()
		api.authenticate()

		# Download the dataset
		api.dataset_download_file(dataset, file_name=filename, path=downloadPath, force=True)

		# Unzip if it's a zip file
		if (zipFilePath := Path(str(filePath) + '.zip')).exists():
			with ZipFile(zipFilePath) as zip:
				zip.extractall(path=downloadPath)

			os.remove(zipFilePath)

		# Check if file exists
		if not filePath.exists():
			self.stdout.write(self.style.ERROR(f'File {filePath} not found in the downloaded dataset'))

		### Load file depending on what dataset it is
		# 2024 Paris Olympics
		if filename == 'athletes.csv':
			self.import_athletes_paris2024(filePath)
		if filename == 'events.csv':
			self.import_events_paris2024(filePath)
		if filename == 'medals.csv':
			self.import_medals_paris2024(filePath)
		if filename == 'teams.csv':
			self.import_teams_paris2024(filePath)

		# 1896–2022 Olympics
		if filename == 'olympic_medals.csv':
			self.import_medals_all(filePath)
		if filename == 'olympic_hosts.csv':
			self.import_hosts_all(filePath)


	def import_medals_all(self, filepath):
		def handle_user_input(name, iso_code):
			user_input = input(f"Custom flag URL for {name}? (leave blank to pass): ").strip()

			return user_input if user_input else "https://upload.wikimedia.org/wikipedia/commons/2/2f/Missing_flag.png"

		try:
			with open(filepath, newline='') as file:
				reader = csv.DictReader(file)
				for row in reader:
					print(row['country_name'])
					print(row['country_3_letter_code'], '\n')
					try:
						country = Country.objects.get(code=row['country_3_letter_code'])

					except Country.DoesNotExist:
						print(row['country_name'])
						print(row['country_3_letter_code'])

						flagURL = f"https://raw.githubusercontent.com/hampusborgos/country-flags/main/png250px/{row['country_code'].lower()}.png"
						try:
							response = requests.head(flagURL)
							if response.status_code != 200:
								print(f"No flag found at {flagURL}. Status code: {response.status_code}")
								flagURL = handle_user_input(row['country_name'], row['country_code'])

						except requests.RequestException as e:
							print(f"Error checking flag URL: {e}")
							flagURL = handle_user_input(row['country_name'], row['country_code'])

						country = Country.objects.create(code=row['country_3_letter_code'], fullName=row['country_name'], iso=row['country_code'], flagURL=flagURL)


					eventName = row['event_title']
					gender = row['event_gender']
					#print(row['discipline_title'])
					disciplineName = row['discipline_title']
					if disciplineName == 'Volleyball':
						disciplineName = 'Indoor Volleyball'
					elif disciplineName == 'Baseball/Softball':
						disciplineName = 'Baseball'

					try:
						discipline = Discipline.objects.get(name__iexact=disciplineName)
					except ObjectDoesNotExist:
						if disciplineName == 'Equestrian':
							#print(f"{disciplineName} {eventName.split(' ')[0]}")
							discipline = Discipline.objects.get(name=f"{disciplineName} {eventName.split(' ')[0]}")

					year = int(row['slug_game'].split('-')[-1])

					try:
						host = Host.objects.get(slug=row['slug_game'])
					except host.DoesNotExist:
						self.stdout.write(self.style.ERROR(f'Host game does not exist for "{year}"'))

					event, created = Event.objects.get_or_create(discipline=discipline, name=eventName, gender=gender, host=host)

					if row['participant_type'] == 'Athlete':
						winnerContentType = ContentType.objects.get_for_model(Athlete)
						winner, created = Athlete.objects.get_or_create(
							name=row['athlete_full_name'],
							gender=gender,
							country=country
						)

					else:
						winnerContentType = ContentType.objects.get_for_model(Team)

						if gender == "Women": genderCode = 'W'
						elif gender == "Men": genderCode = 'M'
						elif gender == "Mixed": genderCode = 'X'
						else: genderCode = 'O'

						eventCode = eventName[:8].ljust(8, '-')

						teamIdPrefix = f'{discipline.code}{genderCode}{eventCode}{country.code}{year}'
						existingTeams = Team.objects.filter(id__startswith=teamIdPrefix).order_by('-id')

						if existingTeams.exists():
							# Extract the latest team number and increment it
							latestTeam = existingTeams.first()
							latestTeamNumber = int(latestTeam.id[-6:-4])  # Get the last two characters as an integer
							newTeamNumber = latestTeamNumber + 1
							teamNumberCode = f"{newTeamNumber:02d}"  # Format as 2 digits
						else:
							teamNumberCode = '01'

						teamId = f'{teamIdPrefix}{teamNumberCode}'.upper()
						
						winner, created = Team.objects.get_or_create(
							id=teamId,
							defaults=dict(
								country=country,
								gender=gender,
								discipline=discipline,
							)
						)

					Medal.objects.update_or_create(
						country=country,
						rank=row['medal_type'].capitalize(),
						event=event,
						content_type=winnerContentType,
						object_id=winner.id,
						date=date(year, 1, 1),
					)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {filepath}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{filepath}" not found'))

	def import_hosts_all(self, filepath):
		try:
			with open(filepath, newline='') as file:
				reader = csv.DictReader(file)
				for row in reader:
					Host.objects.update_or_create(
						id=row['game_slug'],
						name=row['game_name'],
						slug=row['game_slug'],
						location=row['game_location'],
						season=row['game_season'],
						year=row['game_year'],
						startDate=row['game_start_date'],
						endDate=row['game_end_date'],
					)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {filepath}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{filepath}" not found'))
		except:
			self.stdout.write(self.style.ERROR(f'Unknown error with the following row:\n{row}'))

	def import_teams_paris2024(self, filepath):
		year = 2024
		try:
			with open(filepath, newline='') as file:
				reader = csv.DictReader(file)
				for row in reader:
					country, created = Country.objects.get_or_create(code=row['country_code'], defaults={'fullName': row['country']})
					
					if row['current'] == 'True':
						teamId = f"{row['code'][:-2]}{year}{row['code'][-2:]}"

						disciplineCode = row['code'][0:3]
						genderCode = row['code'][3]
						eventCode = row['code'][4:12].replace('-', '')
						countryCode = row['code'][12:15]
						teamNumberCode = row['code'][15:17]

					else:
						disciplineCode = row['disciplines_code']
						genderCode = row['team_gender']
						if row['events']:
							if "Women's" in row['events']:
								eventName = row['events'].split("Women's ")[-1]
							elif "Men's" in row['events']:
								eventName = row['events'].split("Men's ")[-1]
							elif "Mixed" in row['events']:
								eventName = row['events'].split("Mixed ")[-1]
							else:
								eventName = row['events']
						else:
							eventName = row['discipline']

						eventCode = eventName[:8].ljust(8, '-')
						countryCode = row['country_code']

						teamIdPrefix = f'{disciplineCode}{genderCode}{eventCode}{countryCode}{year}'
						existingTeams = Team.objects.filter(id__startswith=teamIdPrefix).order_by('-id')

						if existingTeams.exists():
							# Extract the latest team number and increment it
							latestTeam = existingTeams.first()
							latestTeamNumber = int(latestTeam.id[-2:])  # Get the last two characters as an integer
							newTeamNumber = latestTeamNumber + 1
							teamNumberCode = f"{newTeamNumber:02d}"  # Format as 2 digits
						else:
							teamNumberCode = '01'

						teamId = f'{teamIdPrefix}{teamNumberCode}'.upper()

					numAthletes = 0 if row['num_athletes'] == '' else int(float(row['num_athletes']))
					Team.objects.update_or_create(
						id=teamId,
						defaults={
							'country': country,
							'gender': row['team_gender'],
							'discipline': row['discipline'],
							'athleteNames': row['athletes'],
							'athleteIDs': row['athletes_codes'],
							'numAthletes': numAthletes,
							'codeRaw': row['code'],
						}
					)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {filepath}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{filepath}" not found'))
		except:
			self.stdout.write(self.style.ERROR(f'Unknown error with the following row:\n{row}'))


	def import_events_paris2024(self, filepath):
		try:
			with open(filepath, newline='') as file:
				reader = csv.DictReader(file)
				for row in reader:

					sport = row['sport']
					if "Men" in row['event'] or 'Boy' in row['event']:
						gender = 'M'
						name = row['event'].replace('Men', '').replace("'s", "").strip()
					elif "Women" in row['event'] or "Girl" in row['event']:
						gender = 'W'
						name = row['event'].replace('Women', '').replace("'s", "").strip()
					elif "Mixed" in row['event']:
						gender = 'X'
						name = row['event'].replace('Mixed', '').strip()
					elif sport in ['Artistic Swimming', 'Rhythmic Gymnastics']:
						name = row['event']
						gender = 'W'
					elif sport == 'Equestrian':
						name = row['event']
						gender = 'O'
					else:
						self.stdout.write(self.style.ERROR(f"Event {row['event']} can't be coerced into GENDER / EVENTNAME"))

					try:
						discipline = Discipline.objects.get(code=row['sport_code'])

					except ObjectDoesNotExist:
						print(sport)
						if sport== 'Equestrian':
							print(f"{sport} {row['event'].split(' ')[0]}")
							discipline = Discipline.objects.get(name=f"{sport} {row['event'].split(' ')[0]}")
						else:
							print(f'Discipline {row['sport_code']} does not exist')
							discipline = Discipline.objects.get_or_create(code='OTH')

					event, created = Event.objects.update_or_create(
						discipline=discipline,
						name=name,
						gender=gender,
						host=Host.objects.get(id='paris-2024')
					)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {filepath}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{filepath}" not found'))


	def import_medals_paris2024(self, filepath):
		year = 2024
		host = Host.objects.get(year=year)
		try:
			with open(filepath, newline='') as file:
				reader = csv.DictReader(file)
				for row in reader:
					country, created = Country.objects.get_or_create(code=row['country_code'])

					# Make sure the event exists
					split = row['event'].split("'s ")
					if len(split) == 1:
						name = split[0]
						gender = 'Mixed'
					elif len(split) == 2:
						name = split[1]
						gender = split[0]
					else:
						self.stdout.write(self.style.ERROR(f"Event {row['event']} can't be coerced into GENDER / EVENTNAME"))

					print(row['discipline'])
					try:
						discipline = Discipline.objects.get(name=row['discipline'])
					except ObjectDoesNotExist:
						if row['discipline'] == 'Equestrian':
							print(f"{row['discipline']} {row['event'].split(' ')[0]}")
							discipline = Discipline.objects.get(name=f"{row['discipline']} {row['event'].split(' ')[0]}")

					print(discipline)
					event, created = Event.objects.get_or_create(name=row['event'], discipline=discipline, gender=gender, host=host)

					if 'ATH' in row['event_type']:
						winnerContentType = ContentType.objects.get_for_model(Athlete)
						winner = Athlete.objects.get(id=row['code'])
					else:
						winnerContentType = ContentType.objects.get_for_model(Team)
						winner = Team.objects.get(id=f"{row['code'][:-2]}{year}{row['code'][-2:]}")

					Medal.objects.update_or_create(
						country=country,
						rank=row['medal_type'].split(' Medal')[0],
						event=event,
						content_type=winnerContentType,
						object_id=winner.id,
						defaults={'date': row['medal_date']},
					)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {filepath}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{filepath}" not found'))

		#except:	
			#self.stdout.write(self.style.ERROR(f'Unknown error with the following row:\n{row}'))


	def import_athletes_paris2024(self, filepath):
		try:
			with open(filepath, newline='') as file:
				reader = csv.DictReader(file)
				for row in reader:
					print(row['country_code'])
				
					country = Country.objects.get(code=row['country_code'])

					print(country)
					#self.stdout.write(self.style.SUCCESS(f'Country {country.fullName} created or found'))
					Athlete.objects.update_or_create(
							id = row['code'],
							name = row['name'],
							shortName = row['name_short'],
							displayName = row['name_tv'],
							gender = row['gender'],
							country = country,
							disciplines = row['disciplines'],
							events = row['events'],
							dob=row['birth_date'],
							height=row['height'] if row['height'] != '' else 0.0,
							weight=row['weight'] if row['weight'] != '' else 0.0,
							isAlternate=True if row['function'] == 'Alternate Athlete' else False
						)

			self.stdout.write(self.style.SUCCESS(f'Successfully imported data from {filepath}'))
		except FileNotFoundError:
			self.stdout.write(self.style.ERROR(f'File "{filepath}" not found'))
		except:
			self.stdout.write(self.style.ERROR(f'Unknown error with the following row:\n{row}'))


