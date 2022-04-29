from django.core.validators import MinLengthValidator
from django.db import models


# Create your models here.
class User(models.Model):
    username = models.CharField(verbose_name="Username", max_length=32, validators=[MinLengthValidator(4)])
    password = models.CharField(verbose_name="Password", max_length=32, validators=[MinLengthValidator(4)])
    email = models.EmailField(verbose_name="Email", max_length=64)


class Record(models.Model):
    user = models.ForeignKey(to="weather.User", on_delete=models.PROTECT, to_field="id")
    fips = models.CharField(verbose_name="FIPS", max_length=5)
    interval = models.CharField(verbose_name="Interval", max_length=7)
    coverage = models.IntegerField(verbose_name="Coverage")
    level = models.IntegerField(verbose_name="Level")
    prediction = models.IntegerField(verbose_name="Prediction")
    price = models.FloatField(verbose_name="Price")


class Coordinate(models.Model):
    fips = models.CharField(max_length=5)
    longitude = models.CharField(max_length=128)
    latitude = models.CharField(max_length=128)
