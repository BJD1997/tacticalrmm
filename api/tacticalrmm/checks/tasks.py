import datetime as dt
import random
from time import sleep

from tacticalrmm.celery import app
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone as djangotime

from agents.models import Agent
from clients.models import Client, Site


@app.task
def handle_check_email_alert_task(pk):
    from .models import Check

    check = Check.objects.get(pk=pk)

    # first time sending email
    if not check.email_sent:
        sleep(random.randint(1, 10))
        check.send_email()
        check.email_sent = djangotime.now()
        check.save(update_fields=["email_sent"])
    else:
        # send an email only if the last email sent is older than 24 hours
        delta = djangotime.now() - dt.timedelta(hours=24)
        if check.email_sent < delta:
            sleep(random.randint(1, 10))
            check.send_email()
            check.email_sent = djangotime.now()
            check.save(update_fields=["email_sent"])

    return "ok"


@app.task
def run_checks_task(pk):
    agent = Agent.objects.get(pk=pk)
    agent.salt_api_async(func="win_agent.run_manual_checks")
    return "ok"
