from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.text import slugify


# Create your models here.
class Country(models.Model):
	fullName = models.CharField(max_length=264, primary_key=True)
	code = models.CharField(max_length=3, unique=True)
	iso = models.CharField(max_length=6, unique=False, default='xx')
	flagURL = models.URLField()

	def __str__(self):
		return f"{self.fullName}"

	# def get_absolute_url(self):
	# 	return reverse('posts:single', kwargs={'username': self.user.username, 'pk': self.pk})


class Host(models.Model):

	id = models.CharField(max_length=100, primary_key=True)
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=30)
	location = models.CharField(max_length=264)
	season = models.CharField(max_length=6, choices=[('Winter', 'Winter'), ('Summer', 'Summer')])
	year = models.IntegerField()
	startDate = models.DateTimeField()
	endDate = models.DateTimeField()

	def get_latest_host():
		return Host.objects.order_by('-year').first()

	def save(self, *args, **kwargs):
		# Auto-generate the slug from the city and year if not provided
		if not self.slug:
			self.slug = slugify(f'{self.id}')

		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.name}"


class Athlete(models.Model):
	GENDER_CHOICES = [
		('Male', "Male"),
		('Female', "Female"),
		# ('X': "Non-Binary")
	]

	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=264)
	shortName = models.CharField(max_length=264, blank=True)
	displayName = models.CharField(max_length=264, blank=True)
	gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
	country = models.ForeignKey(Country, related_name='athletes', on_delete=models.CASCADE)
	disciplines = models.CharField(max_length=1000, blank=True)
	events = models.CharField(max_length=1000, blank=True)
	dob = models.DateField(null=True)
	height = models.DecimalField(max_digits=5, decimal_places=2, null=True)
	weight = models.DecimalField(max_digits=5, decimal_places=2, null=True)
	isAlternate = models.BooleanField(null=True)

	medals = GenericRelation('Medal')
	
	def __str__(self):
		return f"{self.displayName if self.displayName != '' else self.name}"


class Team(models.Model):
	
	MEN = 'M'; WOMEN = 'W'; MIXED = 'X'
	GENDER_CHOICES = [
		(MEN, "Men"),
		(WOMEN, "Women"),
		(MIXED, "Mixed")
	]

	id = models.CharField(max_length=50, primary_key=True)
	country = models.ForeignKey(Country, related_name='teams', on_delete=models.CASCADE)
	gender = models.CharField(max_length=5, choices=GENDER_CHOICES)
	discipline = models.CharField(max_length=264)
	athleteNames = models.CharField(max_length=1000, blank=True)
	athleteIDs = models.CharField(max_length=1000, blank=True)
	numAthletes = models.IntegerField(null=True)
	codeRaw = models.CharField(max_length=30, blank=True)

	medals = GenericRelation('Medal')

	def __str__(self):
		return f"{self.gender} {self.discipline} from {self.country}"


class Discipline(models.Model):

	code = models.CharField(max_length=3, primary_key=True)
	name = models.CharField(max_length=264)
	sport = models.CharField(max_length=264, blank=True)

	def __str__(self):
		return f"{self.name}"


class Event(models.Model):

	MEN = 'M'; WOMEN = 'W'; MIXED = 'X'
	GENDER_CHOICES = [
		(MEN, "Men"),
		(WOMEN, "Women"),
		(MIXED, "Mixed")
	]

	name = models.CharField(max_length=264, blank=True, default='')
	discipline = models.ForeignKey(Discipline, related_name='events', on_delete=models.CASCADE)
	gender = models.CharField(max_length=5, choices=GENDER_CHOICES)
	host = models.ForeignKey(Host, related_name='events', on_delete=models.CASCADE)
	
	class Meta:
		unique_together = ('discipline', 'name', 'gender', 'host')

	def __str__(self):
		return f"{self.gender}'s {self.discipline}{': ' if self.name else ''}{self.name}"


class Medal(models.Model):
	GOLD = 'Gold'
	SILVER = 'Silver'
	BRONZE = 'Bronze'
	MEDAL_CHOICES = [
		(GOLD, 'Gold'),
		(SILVER, 'Silver'),
		(BRONZE, 'Bronze'),
	]
	
	rank = models.CharField(max_length=6, choices=MEDAL_CHOICES)
	event = models.ForeignKey(
		Event,
		related_name='medals',
		on_delete=models.CASCADE
	)

	country = models.ForeignKey(Country, related_name='medals', on_delete=models.CASCADE)

	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
	object_id = models.CharField(max_length=264)
	# winner = models.ForeignKey(
	# 	Athlete,
	# 	related_name='medals',
	# 	on_delete=models.CASCADE
	# )
	content_object = GenericForeignKey('content_type', 'object_id')

	date = models.DateField(null=True)

	class Meta:
		indexes = [
			models.Index(fields=["content_type", "object_id"]),
		]

	# def save(self, *args, **kwargs):
	# 	if not self.pk:  # Only validate new medals
	# 		if Medal.objects.filter(event=self.event, rank=self.rank).exists():
	# 			raise ValidationError(f"{self.get_rank_display()} medal already assigned for {self.event}.")
	# 	super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.event} [{self.rank}]"
