from django.urls import path
from . import views

app_name = 'kb'

urlpatterns = [
    path('', views.home, name='home'),
    path('chat/', views.chat, name='chat'),
    path('chat/answer/', views.chat_answer, name='chat_answer'),
    path('chat/think/', views.chat_think, name='chat_think'),
    path('chat/mode/', views.set_mode, name='set_mode'),
    path('export/', views.export_view, name='export'),
    path('import/', views.import_view, name='import'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
