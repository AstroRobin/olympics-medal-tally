from django.db.models import Count, Case, When, IntegerField, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic

from django.http import JsonResponse

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from tally_app.models import Country, Athlete, Team, Medal, Event, Host

# Create your views here.
# def index(request):
# 	return render(request, 'tally_app/index.html')


def index(request):

	# Annotate each country with the total number of medals
	countries = Country.objects.annotate(
		num_gold_medals=Count(
			Case(
				When(medals__rank=Medal.GOLD, then=1),
				output_field=IntegerField()
			)
		),
		num_silver_medals=Count(
			Case(
				When(medals__rank=Medal.SILVER, then=1),
				output_field=IntegerField()
			)
		),
		num_bronze_medals=Count(
			Case(
				When(medals__rank=Medal.BRONZE, then=1),
				output_field=IntegerField()
			)
		),
		total_medals=Count('medals')
	).order_by('-num_gold_medals', '-num_silver_medals', '-num_bronze_medals')

	hosts = Host.objects.all()
	medals = Medal.objects.filter()

	context = {
		'countries': countries,
		'top_countries': countries[0:10],
		'medals': medals,
		'hosts': hosts.order_by('-year')
	}

	return render(request, 'tally_app/index.html', context=context)


# View to display and update the current Host
def all_games(request):
	season_filter = request.GET.get('season', 'All')  # Default to "All" if no filter is set

	if season_filter == 'Summer':
		hosts = Host.objects.filter(season='Summer')
	elif season_filter == 'Winter':
		hosts = Host.objects.filter(season='Winter')
	else:
		hosts = Host.objects.all()  # Show all hosts for "All"

	context = {
		'hosts': hosts.order_by('-year'),
		'season_filter': season_filter,  # Pass the current filter to the template
	}
	return render(request, 'tally_app/games.html', context)


def all_countries(request):
	countries = Country.objects.all()

	num_columns_md = 4  # Number of columns for medium and larger screens
	num_columns_sm = 2  # Number of columns for small screens
	num_columns_xs = 1  # Number of columns for extra small screens

	countries = Country.objects.annotate(total_medals=Count('medals')).order_by('-total_medals')

	hosts = Host.objects.all().order_by('-year')

	context = {
		'hosts': hosts,
		'countries': countries,
		'top_countries': countries.order_by('-total_medals')[0:10],
		'num_columns_md': 12 // num_columns_md,
		'num_columns_sm': 12 // num_columns_sm,
		'num_columns_xs': 12 // num_columns_xs,
		'num_columns': num_columns_md,  # used for row wrapping logic
	}

	return render(request, 'tally_app/countries.html', context=context)


def country_medals(request, code):
	country = get_object_or_404(Country, code=code)
	medals = Medal.objects.filter(country=country)

	uniqueDisciplines = Event.objects.filter(medals__in=medals).values_list('discipline', flat=True).distinct()

	medalsPerDiscipline = {}
	for medal in Medal.objects.filter(country=country):
		if medal.event.discipline not in medalsPerDiscipline:
			medalsPerDiscipline[medal.event.discipline] = []

		medalsPerDiscipline[medal.event.discipline].append(medal)


	# Annotate each country with the total number of medals
	countries = Country.objects.annotate(total_medals=Count('medals')).order_by('-total_medals')

	hosts = Host.objects.all().order_by('-year')

	context = {
		'hosts': hosts,
		'country': country,
		'top_countries': countries[0:10],
		'medalsPerDiscipline': medalsPerDiscipline,
		'disciplines': uniqueDisciplines,
	}

	return render(request, 'tally_app/country_medals.html', context=context)


def country_medal_tally_for_host(request, code, slug):
	country = get_object_or_404(Country, code=code)

	allHosts = Host.objects.all()
	host = get_object_or_404(Host, slug=slug)

	medals = Medal.objects.filter(date__year=host.year, country=country)

	uniqueDisciplines = Event.objects.filter(medals__in=medals).values_list('discipline', flat=True).distinct()

	medalsPerDiscipline = {}
	for medal in medals:
		if medal.event.discipline not in medalsPerDiscipline:
			medalsPerDiscipline[medal.event.discipline] = []

		medalsPerDiscipline[medal.event.discipline].append(medal)

	# Annotate each country with the total number of medals
	countries = Country.objects.filter(medals__in=Medal.objects.filter(date__year=host.year)).distinct().annotate(total_medals=Count('medals')).order_by('-total_medals')

	context = {
		'hosts': allHosts.order_by('-year'),
		'current_host': host,
		'top_countries': countries[0:10],
		'country': country,
		'medalsPerDiscipline': medalsPerDiscipline,
		'disciplines': uniqueDisciplines,
	}

	return render(request, 'tally_app/country_medals_for_host.html', context=context)


def country_stats(request, code):
	# Annotate each country with the total number of medals
	countries = Country.objects.annotate(total_medals=Count('medals')).order_by('-total_medals')
	country = get_object_or_404(Country, code=code)

	season_filter = request.GET.get('season', 'All')  # Default to "All" if no filter is set
	if season_filter == 'Summer':
		hosts = Host.objects.filter(season='Summer')
	elif season_filter == 'Winter':
		hosts = Host.objects.filter(season='Winter')
	else:
		hosts = Host.objects.all()  # Show all hosts for "All"


	# Annotate hosts with the medal counts
	medalData = hosts.annotate(
		num_gold_medals=Count('events__medals', filter=Q(events__medals__country=country, events__medals__rank='Gold')),
		num_silver_medals=Count('events__medals', filter=Q(events__medals__country=country, events__medals__rank='Silver')),
		num_bronze_medals=Count('events__medals', filter=Q(events__medals__country=country, events__medals__rank='Bronze')),
		total_medals=Count('events__medals', filter=Q(events__medals__country=country))
	).order_by('year')

	# Prepare the data for Plotly
	data = {
		'year': [host.year for host in medalData],
		'Total Medals': [host.total_medals for host in medalData],
		'Gold Medals': [host.num_gold_medals for host in medalData],
		'Silver Medals': [host.num_silver_medals for host in medalData],
		'Bronze Medals': [host.num_bronze_medals for host in medalData],
	}

	df = pd.DataFrame(data)

	cmin = min(df['Total Medals'].values)  # get minimum value of the whole set
	cmax = max(df['Total Medals'].values)  # get maximum value of the whole set

	fig = go.Figure()

	colors = [ 'black', '#e8c62c', 'silver', '#e6a14e']

	for ii, col in enumerate(df.columns[1:]):
		fig.add_trace(
			go.Scatter(
				x=df['year'],  # construct list of identical X values to match the Y-list
				y=df[col],  # Your MTU list
				mode='lines+markers',  # scatter plot without lines
				marker=dict(
					color=colors[ii],  # set color by the value of Y
					cmin=cmin,  # absolute color scaling min value
					cmax=cmax,  # absolute color scaling max value
				),
				line=dict(
					dash='dot' if ii == 0 else 'solid',
				),
				name=col,
			)
		)

	fig.update_layout(title=f'{country.fullName} Medal Count (1896 - 2024)',
				   xaxis_title='Year',
				   yaxis_title='# Medals')

	chart = fig.to_html()

	context = {
		'hosts': hosts.order_by('-year'),
		'season_filter': season_filter,  # Pass the current filter to the template
		'top_countries': countries[0:10],
		'country': country,
		'chart': chart,
	}

	return render(request, 'tally_app/country_stats.html', context=context)


def host_medal_tally(request, slug):
	allHosts = Host.objects.all()
	host = get_object_or_404(Host, slug=slug)

	medalsForHost = Medal.objects.filter(date__year=host.year)

	countries = Country.objects.filter(medals__in=medalsForHost).distinct().annotate(
		num_gold_medals=Count(
			Case(
				When(medals__rank=Medal.GOLD, then=1),
				output_field=IntegerField()
			)
		),
		num_silver_medals=Count(
			Case(
				When(medals__rank=Medal.SILVER, then=1),
				output_field=IntegerField()
			)
		),
		num_bronze_medals=Count(
			Case(
				When(medals__rank=Medal.BRONZE, then=1),
				output_field=IntegerField()
			)
		),
		total_medals=Count('medals')
	)

	context = {
		'countries': countries.order_by('-num_gold_medals', '-num_silver_medals', '-num_bronze_medals'),
		'top_countries': countries.order_by('-total_medals')[0:10],
		'current_host': host,
		'hosts': allHosts.order_by('-year'),
	}

	return render(request, 'tally_app/host_medal_tally.html', context=context)


def event_detail(request, pk):
	event = get_object_or_404(Event, id=pk)  # Fetch the event
	medals = Medal.objects.filter(event=event).order_by('rank')  # Get gold, silver, bronze medals

	context = {
		'event': event,
		'gold_medal': medals.filter(rank='Gold').first(),
		'silver_medal': medals.filter(rank='Silver').first(),
		'bronze_medal': medals.filter(rank='Bronze').first(),
	}
	return render(request, 'tally_app/event_detail.html', context)
