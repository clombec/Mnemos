from django.urls import path
from . import views

app_name = 'kb'

urlpatterns = [
    path('', views.home, name='home'),
    path('chat/', views.chat, name='chat'),
    path('chat/answer/', views.chat_answer, name='chat_answer'),
    path('chat/think/', views.chat_think, name='chat_think'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
