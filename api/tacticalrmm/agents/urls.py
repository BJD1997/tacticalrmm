from django.urls import path
from . import views

urlpatterns = [
    path("listagents/", views.list_agents),
    path("listagentsnodetail/", views.list_agents_no_detail),
    path("byclient/<client>/", views.by_client),
    path("bysite/<client>/<site>/", views.by_site),
    path("overdueaction/", views.overdue_action),
    path("sendrawcmd/", views.send_raw_cmd),
    path("<pk>/agentdetail/", views.agent_detail),
    path("<int:pk>/meshcentral/", views.meshcentral),
    path("poweraction/", views.power_action),
    path("uninstall/", views.uninstall),
    path("editagent/", views.edit_agent),
    path("<pk>/geteventlog/<logtype>/<days>/", views.get_event_log),
    path("getagentversions/", views.get_agent_versions),
    path("updateagents/", views.update_agents),
    path("<pk>/getprocs/", views.get_processes),
    path("<pk>/<pid>/killproc/", views.kill_proc),
    path("rebootlater/", views.reboot_later),
    path("installagent/", views.install_agent),
    path("<int:pk>/ping/", views.ping),
    path("recover/", views.recover),
]
