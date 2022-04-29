from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, HttpResponse
from team7.myutils import form_util, msg_util
from django import forms
from datetime import datetime
import re
import weather.utils
import weather.dsmodel

# Create your views here.
from weather.models import User


class LoginForm(form_util.BootstrapForm):
    username = forms.CharField(label="Username", widget=forms.TextInput())
    password = forms.CharField(label="Password", widget=forms.PasswordInput())

    def clean_username(self):
        input_username = self.cleaned_data.get("username")
        if len(input_username) < 4 or len(input_username) > 32:
            raise ValidationError("Illegal length")
        return input_username

    def clean_password(self):
        input_password = self.cleaned_data.get("password")
        if len(input_password) < 4 or len(input_password) > 32:
            raise ValidationError("Illegal length")
        return input_password

    def clean(self):
        input_username = self.cleaned_data.get("username")
        input_password = self.cleaned_data.get("password")
        print(input_username, input_password)
        if input_username is None or input_password is None:
            return self.cleaned_data
        current_user = User.objects.filter(username=input_username).first()
        if current_user is None or current_user.password != input_password:
            self.add_error("password", "Incorrect username or password")
            raise ValidationError("Incorrect username or password")
        return self.cleaned_data


def login(request, *args, **kwargs):
    if request.method == "GET":
        form = LoginForm()
        return render(request, "login.html", {"form": form, "msgs": kwargs.get("msgs")})
    form = LoginForm(request.POST)
    if form.is_valid():
        request.session["info"] = {"username": form.cleaned_data.get("username")}
        return redirect("/home/")
    return render(request, "login.html", {"form": form,
                                          "msgs": kwargs.get("msgs")})


class RegisterForm(form_util.BootstrapModelForm):
    re_password = forms.CharField(label="Confirm Password", required=True, widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ["username", "password", "re_password", "email"]
        widgets = {
            "username": forms.TextInput(),
            "password": forms.PasswordInput(),
            "email": forms.TextInput(),
        }

    def clean_username(self):
        input_username = self.cleaned_data.get("username")
        if User.objects.filter(username=input_username).first() is not None:
            raise ValidationError("Repeated username")
        return input_username

    def clean_email(self):
        input_email = self.cleaned_data.get("email")
        if User.objects.filter(email=input_email).first() is not None:
            raise ValidationError("Repeated email")
        return input_email

    def clean(self):
        input_username = self.cleaned_data.get("username")
        input_password = self.cleaned_data.get("password")
        input_re_password = self.cleaned_data.get("re_password")
        if input_username is None or input_password is None or input_re_password is None:
            return self.cleaned_data
        if input_password != input_re_password:
            self.add_error('re_password', 'Passwords unmatched')
            raise ValidationError("passwords unmatched")
        return self.cleaned_data


def register(request, *args, **kwargs):
    if request.method == "GET":
        form = RegisterForm()
        return render(request, "register.html", {"form": form,
                                                 "msgs": kwargs.get("msgs")})
    form = RegisterForm(request.POST)
    if form.is_valid():
        form.save()
        msg_util.add_session_msg(request,
                                 "success",
                                 "Successfully register, please login with your username and password")
        return redirect("/login/")
    return render(request, "register.html", {"form": form,
                                             "msgs": kwargs.get("msgs")})


def logout(request, *args, **kwargs):
    request.session.clear()
    msg_util.add_session_msg(request, "success", "Successfully logout")
    return redirect("/login/")


def home(request, *args, **kwargs):
    return render(request, "home.html", {"msgs": kwargs.get("msgs")})


class InsuranceForm(form_util.BootstrapForm):
    cur_year = datetime.now().year
    cur_month = datetime.now().month
    choices = [("", "-- Select time --")]

    for i in range(1, 7):
        cur_month += 1
        if cur_month > 12:
            cur_month -= 12
            cur_year += 1
        year_month = str(cur_year) + '-' + str(cur_month)
        choices.append((year_month, year_month))

    fips = forms.CharField(label="FIPS code",
                           widget=forms.TextInput(attrs={"placeholder": "5-digit FIPS code"}))
    interval = forms.ChoiceField(label="Covered month",
                                 choices=choices)
    amount = forms.IntegerField(label="Coverage (Between $0 and $100,000)")
    level = forms.ChoiceField(label="Drought level",
                              choices=((0, "D0"),
                                       (1, "D1"),
                                       (2, "D2"),
                                       (3, "D3"),
                                       (4, "D4")))

    def clean_fips(self):
        input_fips = self.cleaned_data.get("fips")
        if not re.match(r'^[0-9]{5}$', input_fips):
            raise ValidationError("Illegal FIPS code format")
        return input_fips

    def clean_amount(self):
        input_amount = self.cleaned_data.get("amount")
        if input_amount <= 0 or input_amount > 100000:
            raise ValidationError("Illegal amount")
        return input_amount


def insurance(request, *args, **kwargs):
    if request.method == "GET":
        form = InsuranceForm()
        return render(request, "insurance-input.html", {"form": form,
                                                        "msgs": kwargs.get("msgs")})
    form = InsuranceForm(request.POST)
    if form.is_valid():
        year_month = form.cleaned_data.get("interval")
        fips = form.cleaned_data.get("fips")
        amount = form.cleaned_data.get("amount")
        level = int(form.cleaned_data.get("level"))
        coordinate = weather.utils.get_location(fips)
        if len(coordinate) == 0:
            msg_util.add_session_msg(request, "danger", "We can not find your FIPS code location, please confirm")
            return redirect("/insurance/")
        latest_df = weather.utils.get_latest_data(fips, coordinate[0], coordinate[1])
        month = int(year_month[5: len(year_month)])
        predict_result = weather.dsmodel.pricing(latest_df, amount, level, month)
        user = weather.models.User.objects.filter(username=request.session['info']['username']).first()
        weather.models.Record.objects.create(user=user,
                                             fips=fips,
                                             interval=year_month,
                                             coverage=amount,
                                             level=level,
                                             prediction=predict_result["VC"],
                                             price=predict_result["premium"])
        return render(request, "insurance-output.html", {"year_month": year_month,
                                                         "fips": fips,
                                                         "amount": amount,
                                                         "level": level,
                                                         "premium": round(predict_result["premium"], 2),
                                                         "VC": predict_result["VC"],
                                                         "difference": predict_result["difference"],
                                                         "msgs": kwargs.get("msgs")})
    return render(request, "insurance-input.html", {"form": form,
                                                    "msgs": kwargs.get("msgs")})


def test(request, *args, **kwargs):
    # 06009
    coordinate = weather.utils.get_location('06009')
    latest_df = weather.utils.get_latest_data('06009', coordinate[0], coordinate[1])
    month = 7
    predict_result = weather.dsmodel.pricing(latest_df, 10000, 2, month)
    return HttpResponse(str(predict_result['price']) + '********' + str(predict_result['feedback']))


def premium(request, *args, **kwargs):
    if request.method == "GET":
        return render(request, "premium.html", {"msgs": kwargs.get("msgs")})
    msg_util.add_session_msg(request, "success", "Successfully subscribed")
    return redirect("/home/")
