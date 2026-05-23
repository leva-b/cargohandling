from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client as WebClient, TestCase
from django.urls import reverse

from .external_apis import get_usd_byn_rate, get_world_time
from .forms import RegisterForm
from .models import (
    Article, BodyType, CargoType, Client, CompanyInfo, Contact, Driver,
    GlossaryTerm, JobApplication, Order, Promo, Review, Service, Vacancy, Vehicle,
    VehicleType, validate_adult, validate_phone,
)


class ValidationTests(TestCase):
    def test_phone_validation_accepts_required_format(self):
        validate_phone('+375 (29) 123-45-67')

    def test_phone_validation_rejects_wrong_format(self):
        with self.assertRaises(ValidationError):
            validate_phone('8029 1234567')

    def test_adult_validation_rejects_minor(self):
        with self.assertRaises(ValidationError):
            validate_adult(date.today())


class RegisterFormTests(TestCase):
    def test_register_form_creates_user_and_client_profile(self):
        form = RegisterForm(data={
            'username': 'newclient',
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'birth_date': '1990-01-01',
            'phone': '+375 (29) 123-45-67',
            'address': 'Минск',
            'email': 'newclient@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(User.objects.filter(username='newclient').exists())
        self.assertTrue(Client.objects.filter(user=user).exists())


class OrderAccessTests(TestCase):
    def setUp(self):
        self.web = WebClient()
        self.user = User.objects.create_user('client', password='StrongPass123!')
        self.other_user = User.objects.create_user('other', password='StrongPass123!')
        self.client_profile = Client.objects.create(
            user=self.user,
            first_name='Анна',
            last_name='Клиентова',
            birth_date=date(1990, 1, 1),
            phone='+375 (29) 111-22-33',
        )
        self.other_profile = Client.objects.create(
            user=self.other_user,
            first_name='Олег',
            last_name='Другой',
            birth_date=date(1991, 1, 1),
            phone='+375 (29) 222-33-44',
        )
        self.cargo = CargoType.objects.create(name='Мебель')
        self.service = Service.objects.create(name='Погрузка', price=Decimal('40.00'))
        self.order = Order.objects.create(
            client=self.client_profile,
            cargo_type=self.cargo,
            origin='Минск',
            destination='Гродно',
            distance_km=280,
            price=Decimal('350.00'),
        )
        Order.objects.create(
            client=self.other_profile,
            cargo_type=self.cargo,
            origin='Минск',
            destination='Брест',
            distance_km=350,
            price=Decimal('450.00'),
        )

    def test_closed_orders_api_requires_login(self):
        response = self.web.get(reverse('orders_api'))
        self.assertEqual(response.status_code, 302)

    def test_orders_api_returns_only_current_client_orders(self):
        self.web.login(username='client', password='StrongPass123!')

        response = self.web.get(reverse('orders_api'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['orders']), 1)
        self.assertEqual(response.json()['orders'][0]['id'], self.order.pk)

    def test_client_can_create_order(self):
        self.web.login(username='client', password='StrongPass123!')

        response = self.web.post(reverse('order_create'), data={
            'cargo_type': self.cargo.pk,
            'origin': 'Минск',
            'destination': 'Витебск',
            'distance_km': 300,
            'price': '500.00',
            'status': 'new',
            'services': [self.service.pk],
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(destination='Витебск', client=self.client_profile).exists())


class StatisticsTests(TestCase):
    def test_statistics_page_uses_html_chart_without_javascript(self):
        admin = User.objects.create_superuser('admin', password='StrongPass123!')
        client_user = User.objects.create_user('client', password='StrongPass123!')
        client = Client.objects.create(
            user=client_user,
            first_name='Анна',
            last_name='Клиентова',
            birth_date=date(1990, 1, 1),
            phone='+375 (29) 111-22-33',
        )
        cargo = CargoType.objects.create(name='Стройматериалы')
        Order.objects.create(
            client=client,
            cargo_type=cargo,
            origin='Минск',
            destination='Гомель',
            distance_km=300,
            price=Decimal('600.00'),
            status='delivered',
        )
        web = WebClient()
        web.force_login(admin)

        response = web.get(reverse('statistics'))

        self.assertContains(response, 'Диаграмма')
        self.assertNotContains(response, '<script')
        # PNG chart endpoint exists for superuser
        chart = web.get(reverse('statistics_status_chart'))
        self.assertEqual(chart.status_code, 200)
        self.assertEqual(chart['Content-Type'], 'image/png')
        chart2 = web.get(reverse('statistics_orders_over_time_chart'))
        self.assertEqual(chart2.status_code, 200)
        self.assertEqual(chart2['Content-Type'], 'image/png')


class ExternalApiTests(TestCase):
    def test_world_time_api_parses_response(self):
        response = MagicMock()
        response.read.return_value = (
            b'{"timezone":"Europe/Minsk","datetime":"2026-05-20T20:00:00+03:00",'
            b'"utc_datetime":"2026-05-20T17:00:00+00:00"}'
        )
        response.__enter__.return_value = response

        with patch('cargohandling.external_apis.urlopen', return_value=response):
            data = get_world_time()

        self.assertTrue(data['available'])
        self.assertEqual(data['timezone'], 'Europe/Minsk')

    def test_currency_api_parses_response(self):
        response = MagicMock()
        response.read.return_value = b'{"rates":{"BYN":3.25}}'
        response.__enter__.return_value = response

        with patch('cargohandling.external_apis.urlopen', return_value=response):
            data = get_usd_byn_rate()

        self.assertTrue(data['available'])
        self.assertEqual(data['rate'], 3.25)

    def test_external_api_failure_is_graceful(self):
        with patch('cargohandling.external_apis.urlopen', side_effect=OSError('offline')):
            self.assertFalse(get_usd_byn_rate()['available'])


class PageViewTests(TestCase):
    def setUp(self):
        self.web = WebClient()
        self.superuser = User.objects.create_superuser('admin2', password='StrongPass123!')
        self.user = User.objects.create_user('client2', password='StrongPass123!', first_name='Анна', last_name='Иванова')
        self.driver_user = User.objects.create_user('driver2', password='StrongPass123!', first_name='Петр', last_name='Петров')
        self.client_profile = Client.objects.create(
            user=self.user,
            first_name='Анна',
            last_name='Иванова',
            birth_date=date(1990, 1, 1),
            phone='+375 (29) 333-44-55',
        )
        self.driver = Driver.objects.create(
            user=self.driver_user,
            first_name='Петр',
            last_name='Петров',
            birth_date=date(1985, 1, 1),
            phone='+375 (29) 444-55-66',
            license_number='CD12345',
            experience_years=7,
        )
        self.cargo = CargoType.objects.create(name='Продукты')
        self.service = Service.objects.create(name='Доставка', price=Decimal('100.00'))
        self.body_type = BodyType.objects.create(name='Фургон')
        self.vehicle_type = VehicleType.objects.create(name='Грузовик')
        self.vehicle = Vehicle.objects.create(
            driver=self.driver,
            vehicle_type=self.vehicle_type,
            body_type=self.body_type,
            brand='MAN',
            model='TGL',
            plate_number='AA 1234-7',
            year=2020,
            load_capacity_kg=5000,
        )
        self.order = Order.objects.create(
            client=self.client_profile,
            driver=self.driver,
            vehicle=self.vehicle,
            cargo_type=self.cargo,
            origin='Минск',
            destination='Могилев',
            distance_km=200,
            price=Decimal('350.00'),
        )
        self.order.services.add(self.service)
        self.article = Article.objects.create(
            title='Новая услуга',
            summary='Запущена новая услуга доставки.',
            content='Полный текст статьи.',
        )
        CompanyInfo.objects.create(name='Компания', description='Описание', phone='+375 (29) 555-66-77')
        GlossaryTerm.objects.create(question='Что такое фура?', answer='Большой грузовой автомобиль.')
        Contact.objects.create(full_name='Менеджер Иван', position='Менеджер', phone='+375 (29) 666-77-88')
        Vacancy.objects.create(title='Логист', description='Работа с заказами.')
        Promo.objects.create(
            code='TEST10',
            discount_percent=10,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 12, 31),
        )
        Review.objects.create(user=self.user, rating=5, text='Отличная перевозка груза.')

    @patch('cargohandling.views.get_world_time', return_value={'available': False})
    @patch('cargohandling.views.get_usd_byn_rate', return_value={'available': False})
    def test_public_pages_render(self, *_):
        names = [
            'index', 'about', 'glossary', 'contacts', 'vacancies', 'privacy',
            'articles', 'promos', 'drivers', 'vehicles', 'services', 'reviews',
        ]

        for name in names:
            response = self.web.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

        self.assertEqual(self.web.get(reverse('article_detail', args=[self.article.pk])).status_code, 200)
        self.assertEqual(self.web.get(reverse('driver_detail', args=[self.driver.pk])).status_code, 200)

    def test_login_logout_and_profile(self):
        response = self.web.post(reverse('login'), {'username': 'client2', 'password': 'StrongPass123!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.web.get(reverse('profile')).status_code, 200)
        self.assertEqual(self.web.get(reverse('logout')).status_code, 302)

    def test_orders_list_and_detail_for_client(self):
        self.web.login(username='client2', password='StrongPass123!')

        response = self.web.get(reverse('orders'), {'q': 'Минск', 'status': 'new'})
        self.assertContains(response, 'Могилев')
        self.assertEqual(self.web.get(reverse('order_detail', args=[self.order.pk])).status_code, 200)

    def test_order_edit_by_owner(self):
        self.web.login(username='client2', password='StrongPass123!')

        response = self.web.post(reverse('order_edit', args=[self.order.pk]), {
            'driver': self.driver.pk,
            'vehicle': self.vehicle.pk,
            'cargo_type': self.cargo.pk,
            'origin': 'Минск',
            'destination': 'Витебск',
            'distance_km': 250,
            'price': '400.00',
            'status': 'in_progress',
            'services': [self.service.pk],
        })

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.destination, 'Витебск')

    def test_non_owner_cannot_open_order_detail(self):
        other = User.objects.create_user('stranger', password='StrongPass123!')
        Client.objects.create(
            user=other,
            first_name='Сергей',
            last_name='Чужой',
            birth_date=date(1992, 1, 1),
            phone='+375 (29) 777-88-99',
        )
        self.web.login(username='stranger', password='StrongPass123!')

        response = self.web.get(reverse('order_detail', args=[self.order.pk]))

        self.assertEqual(response.status_code, 302)

    def test_superuser_can_delete_order(self):
        self.web.force_login(self.superuser)

        response = self.web.post(reverse('order_delete', args=[self.order.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())

    def test_driver_can_change_status_but_does_not_see_edit_delete_buttons(self):
        self.web.login(username='driver2', password='StrongPass123!')

        detail = self.web.get(reverse('order_detail', args=[self.order.pk]))

        self.assertContains(detail, 'Изменить статус')
        self.assertContains(detail, self.client_profile.phone)
        self.assertNotContains(detail, 'Редактировать заказ')
        self.assertNotContains(detail, 'Удалить заказ')

        response = self.web.post(reverse('order_status_edit', args=[self.order.pk]), {'status': 'delivered'})

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'delivered')

    def test_vacancy_application_flow_and_admin_decision(self):
        vacancy = Vacancy.objects.create(title='Водитель B', description='Доставка по городу.')
        self.web.login(username='client2', password='StrongPass123!')

        response = self.web.post(reverse('vacancy_apply', args=[vacancy.pk]), {
            'full_name': 'Анна Иванова',
            'phone': '+375 (29) 333-44-55',
            'email': 'anna@example.com',
            'message': 'Хочу работать.',
        })

        self.assertEqual(response.status_code, 302)
        application = JobApplication.objects.get(vacancy=vacancy, user=self.user)
        self.assertEqual(application.status, 'pending')

        self.web.force_login(self.superuser)
        response = self.web.post(reverse('job_application_decide', args=[application.pk]), {
            'status': 'approved',
            'admin_comment': 'Подходит.',
        })

        self.assertEqual(response.status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, 'approved')

    def test_review_form_post(self):
        self.web.login(username='client2', password='StrongPass123!')

        response = self.web.post(reverse('reviews'), {'rating': 4, 'text': 'Все доставили быстро.'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(text='Все доставили быстро.').exists())
