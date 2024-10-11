from django.urls import path, re_path

from . import views

app_name = 'tally'

urlpatterns = [
	re_path(r'country/(?P<code>[-\w]+)/$', views.country_medals, name='country'),
	re_path(r'country/(?P<code>[-\w]+)/stats/$', views.country_stats, name='country_stats'),
	path('host/<slug:slug>/', views.host_medal_tally, name='host_tally'),
	path('country/<slug:code>/<slug:slug>/', views.country_medal_tally_for_host, name='country_tally_for_host'),
	re_path(r'event/(?P<pk>\d+)$', views.event_detail, name='event_detail'),
]
