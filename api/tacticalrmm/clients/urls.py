from django.urls import path
from . import views

urlpatterns = [
    path("clients/", views.GetAddClients.as_view()),
    path("<int:pk>/client/", views.GetUpdateDeleteClient.as_view()),
    path("sites/", views.GetAddSites.as_view()),
    path("listclients/", views.list_clients),
    path("listsites/", views.list_sites),
    path("addsite/", views.add_site),
    path("editsite/", views.edit_site),
    path("deletesite/", views.delete_site),
    path("loadtree/", views.load_tree),
    path("loadclients/", views.load_clients),
    path("deployments/", views.AgentDeployment.as_view()),
    path("<int:pk>/deployment/", views.AgentDeployment.as_view()),
    path("<str:uid>/deploy/", views.GenerateAgent.as_view()),
]
