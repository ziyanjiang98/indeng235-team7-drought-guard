from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import HttpResponse, redirect, render

from team7.myutils.msg_util import add_session_msg


class AuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        url = request.path_info
        print(url)
        if url == "/login/" or url == "/register/" or url == "/" or url == "/logout/" or url == "/favicon.ico":
            return
        info = request.session.get("info")
        if not info:
            add_session_msg(request, "danger", "Please login")
            return redirect("/login/")
        return
