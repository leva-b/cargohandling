from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('privacy/', views.privacy, name='privacy'),
    path('contacts/', views.contacts, name='contacts'),
    path('vacancies/', views.vacancies, name='vacancies'),
    re_path(r'^vacancies/(?P<pk>\d+)/apply/$', views.vacancy_apply, name='vacancy_apply'),
    path('promos/', views.promos, name='promos'),
    path('glossary/', views.glossary, name='glossary'),

    path('news/', views.articles, name='articles'),
    re_path(r'^news/(?P<pk>\d+)/$', views.article_detail, name='article_detail'),
    path('drivers/', views.drivers, name='drivers'),
    re_path(r'^drivers/(?P<driver_id>\d+)/$', views.driver_detail, name='driver_detail'),

    path('vehicles/', views.vehicles, name='vehicles'),
    path('services/', views.services, name='services'),
    path('orders/', views.orders, name='orders'),
    re_path(r'^orders/(?P<pk>\d+)/$', views.order_detail, name='order_detail'),
    path('orders/create/', views.order_create, name='order_create'),
    re_path(r'^orders/(?P<pk>\d+)/edit/$', views.order_edit, name='order_edit'),
    re_path(r'^orders/(?P<pk>\d+)/status/$', views.order_status_edit, name='order_status_edit'),
    re_path(r'^orders/(?P<pk>\d+)/delete/$', views.order_delete, name='order_delete'),
    path('reviews/', views.reviews, name='reviews'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    re_path(r'^profile/applications/(?P<pk>\d+)/decide/$', views.job_application_decide, name='job_application_decide'),
    path('statistics/', views.statistics, name='statistics'),
    path('statistics/chart/status.png', views.statistics_status_chart, name='statistics_status_chart'),
    path('statistics/chart/orders_over_time.png', views.statistics_orders_over_time_chart, name='statistics_orders_over_time_chart'),
    re_path(r'^api/orders/$', views.orders_api, name='orders_api'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
