from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import HttpResponse, redirect, render


class MsgMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        msg_list = request.session.get("msgs", [])
        request.session["msgs"] = []
        view_kwargs["msgs"] = msg_list
        return
