def add_session_msg(request, msg_type, msg_content):
    msgs = request.session.get("msgs", [])
    msgs.append({"type": msg_type, "content": msg_content})
    request.session["msgs"] = msgs
