import string
import os
import json
from statistics import mean

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import CoreSettings

import agents

from .tasks import handle_check_email_alert_task

CHECK_TYPE_CHOICES = [
    ("diskspace", "Disk Space Check"),
    ("ping", "Ping Check"),
    ("cpuload", "CPU Load Check"),
    ("memory", "Memory Check"),
    ("winsvc", "Service Check"),
    ("script", "Script Check"),
    ("eventlog", "Event Log Check"),
]

CHECK_STATUS_CHOICES = [
    ("passing", "Passing"),
    ("failing", "Failing"),
    ("pending", "Pending"),
]

EVT_LOG_NAME_CHOICES = [
    ("Application", "Application"),
    ("System", "System"),
    ("Security", "Security"),
]

EVT_LOG_TYPE_CHOICES = [
    ("INFO", "Information"),
    ("WARNING", "Warning"),
    ("ERROR", "Error"),
    ("AUDIT_SUCCESS", "Success Audit"),
    ("AUDIT_FAILURE", "Failure Audit"),
]

EVT_LOG_FAIL_WHEN_CHOICES = [
    ("contains", "Log contains"),
    ("not_contains", "Log does not contain"),
]


class Check(models.Model):

    # common fields

    agent = models.ForeignKey(
        "agents.Agent",
        related_name="agentchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    policy = models.ForeignKey(
        "automation.Policy",
        related_name="policychecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    managed_by_policy = models.BooleanField(default=False)
    overriden_by_policy = models.BooleanField(default=False)
    parent_check = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    check_type = models.CharField(
        max_length=50, choices=CHECK_TYPE_CHOICES, default="diskspace"
    )
    status = models.CharField(
        max_length=100, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    more_info = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    fails_b4_alert = models.PositiveIntegerField(default=1)
    fail_count = models.PositiveIntegerField(default=0)
    email_sent = models.DateTimeField(null=True, blank=True)
    text_sent = models.DateTimeField(null=True, blank=True)
    outage_history = models.JSONField(null=True, blank=True)  # store
    extra_details = models.JSONField(null=True, blank=True)

    # check specific fields

    # threshold percent for diskspace, cpuload or memory check
    threshold = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    # diskcheck i.e C:, D: etc
    disk = models.CharField(max_length=2, null=True, blank=True)
    # ping checks
    ip = models.CharField(max_length=255, null=True, blank=True)
    # script checks
    script = models.ForeignKey(
        "scripts.Script",
        related_name="script",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    timeout = models.PositiveIntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    retcode = models.IntegerField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, null=True, blank=True)
    # cpu and mem check history
    history = ArrayField(
        models.IntegerField(blank=True), null=True, blank=True, default=list
    )
    # win service checks
    svc_name = models.CharField(max_length=255, null=True, blank=True)
    svc_display_name = models.CharField(max_length=255, null=True, blank=True)
    pass_if_start_pending = models.BooleanField(null=True, blank=True)
    restart_if_stopped = models.BooleanField(null=True, blank=True)
    svc_policy_mode = models.CharField(
        max_length=20, null=True, blank=True
    )  # 'default' or 'manual', for editing policy check

    # event log checks
    log_name = models.CharField(
        max_length=255, choices=EVT_LOG_NAME_CHOICES, null=True, blank=True
    )
    event_id = models.IntegerField(null=True, blank=True)
    event_id_is_wildcard = models.BooleanField(default=False)
    event_type = models.CharField(
        max_length=255, choices=EVT_LOG_TYPE_CHOICES, null=True, blank=True
    )
    fail_when = models.CharField(
        max_length=255, choices=EVT_LOG_FAIL_WHEN_CHOICES, null=True, blank=True
    )
    search_last_days = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        if self.agent:
            return f"{self.agent.hostname} - {self.readable_desc}"
        else:
            return f"{self.policy.name} - {self.readable_desc}"

    @property
    def readable_desc(self):
        if self.check_type == "diskspace":
            return f"{self.get_check_type_display()}: Drive {self.disk} < {self.threshold}%"
        elif self.check_type == "ping":
            return f"{self.get_check_type_display()}: {self.name}"
        elif self.check_type == "cpuload" or self.check_type == "memory":
            return f"{self.get_check_type_display()} > {self.threshold}%"
        elif self.check_type == "winsvc":
            return f"{self.get_check_type_display()}: {self.svc_display_name}"
        elif self.check_type == "eventlog":
            return f"{self.get_check_type_display()}: {self.name}"
        elif self.check_type == "script":
            return f"{self.get_check_type_display()}: {self.script.name}"
        else:
            return "n/a"

    @property
    def history_info(self):
        if self.check_type == "cpuload" or self.check_type == "memory":
            return ", ".join(str(f"{x}%") for x in self.history[-6:])

    @property
    def non_editable_fields(self):
        return [
            "check_type",
            "status",
            "more_info",
            "last_run",
            "fail_count",
            "email_sent",
            "text_sent",
            "outage_history",
            "extra_details",
            "stdout",
            "stderr",
            "retcode",
            "execution_time",
            "history",
            "readable_desc",
            "history_info",
            "parent_check",
            "managed_by_policy",
            "overriden_by_policy",
        ]

    def handle_check(self, data):
        if self.check_type != "cpuload" and self.check_type != "memory":

            if data["status"] == "passing" and self.fail_count != 0:
                self.fail_count = 0
                self.save(update_fields=["fail_count"])

            elif data["status"] == "failing":
                self.fail_count += 1
                self.save(update_fields=["fail_count"])

        else:
            self.history.append(data["percent"])

            if len(self.history) > 15:
                self.history = self.history[-15:]

            self.save(update_fields=["history"])

            avg = int(mean(self.history))

            if avg > self.threshold:
                self.status = "failing"
                self.fail_count += 1
                self.save(update_fields=["status", "fail_count"])
            else:
                self.status = "passing"
                if self.fail_count != 0:
                    self.fail_count = 0
                    self.save(update_fields=["status", "fail_count"])
                else:
                    self.save(update_fields=["status"])

        if self.email_alert and self.fail_count >= self.fails_b4_alert:
            handle_check_email_alert_task.delay(self.pk)

    # for policy diskchecks
    @staticmethod
    def all_disks():
        return [f"{i}:" for i in string.ascii_uppercase]

    # for policy service checks
    @staticmethod
    def load_default_services():
        with open(
            os.path.join(settings.BASE_DIR, "services/default_services.json")
        ) as f:
            default_services = json.load(f)

        return default_services

    def create_policy_check(self, agent):
        Check.objects.create(
            agent=agent,
            managed_by_policy=True,
            parent_check=self.pk,
            name=self.name,
            check_type=self.check_type,
            email_alert=self.email_alert,
            text_alert=self.text_alert,
            fails_b4_alert=self.fails_b4_alert,
            extra_details=self.extra_details,
            threshold=self.threshold,
            disk=self.disk,
            ip=self.ip,
            script=self.script,
            timeout=self.timeout,
            svc_name=self.svc_name,
            svc_display_name=self.svc_display_name,
            pass_if_start_pending=self.pass_if_start_pending,
            restart_if_stopped=self.restart_if_stopped,
            svc_policy_mode=self.svc_policy_mode,
            log_name=self.log_name,
            event_id=self.event_id,
            event_type=self.event_type,
            fail_when=self.fail_when,
            search_last_days=self.search_last_days,
        )

    def is_duplicate(self, check):
        if self.check_type == "diskspace":
            return self.disk == check.disk

        elif self.check_type == "script":
            return self.script == check.script

        elif self.check_type == "ping":
            return self.ip == check.ip

        elif self.check_type == "cpuload":
            return True

        elif self.check_type == "memory":
            return True

        elif self.check_type == "winsvc":
            return self.svc_name == check.svc_name

        elif self.check_type == "eventlog":
            return [self.log_name, self.event_id] == [check.log_name, check.event_id]

    def send_email(self):

        CORE = CoreSettings.objects.first()

        if self.agent:
            subject = f"{self.agent.client}, {self.agent.site}, {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.check_type == "diskspace":
            percent_used = self.agent.disks[self.disk]["percent"]
            percent_free = 100 - percent_used

            body = subject + f" - Free: {percent_free}%, Threshold: {self.threshold}%"

        elif self.check_type == "script":

            body = subject + f" - Return code: {self.retcode}, Error: {self.stderr}"

        elif self.check_type == "ping":

            body = self.more_info

        elif self.check_type == "cpuload" or self.check_type == "memory":

            avg = int(mean(self.history))

            if self.check_type == "cpuload":
                body = (
                    subject
                    + f" - Average CPU utilization: {avg}%, Threshold: {self.threshold}%"
                )

            elif self.check_type == "memory":
                body = (
                    subject
                    + f" - Average memory usage: {avg}%, Threshold: {self.threshold}%"
                )

        elif self.check_type == "winsvc":

            status = list(
                filter(lambda x: x["name"] == self.svc_name, self.agent.services)
            )[0]["status"]

            body = subject + f" - Status: {status.upper()}"

        elif self.check_type == "eventlog":

            body = f"Event ID {self.event_id} was found in the {self.log_name} log"

        CORE.send_mail(subject, body)
