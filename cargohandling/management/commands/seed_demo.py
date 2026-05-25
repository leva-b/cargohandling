from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from cargohandling.models import (
    Article, BodyType, CargoType, Client, CompanyHistory, CompanyInfo,
    Contact, Driver, GlossaryTerm, JobApplication, Order, Organization, Promo, Review,
    Service, Vacancy, Vehicle, VehicleType,
)


class Command(BaseCommand):
    help = 'Заполняет базу демонстрационными данными для задания.'

    def make_image(self, title, color):
        image = Image.new('RGB', (320, 200), color)
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 304, 184), outline=(255, 255, 255), width=4)
        draw.text((32, 88), title[:28], fill=(255, 255, 255))
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return ContentFile(buffer.getvalue())

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin.set_password('admin12345')
        # Keep admin permissions/password deterministic for demo environments.
        admin.is_staff = True
        admin.is_superuser = True
        admin.email = admin.email or 'admin@example.com'
        admin.save()

        company, _ = CompanyInfo.objects.get_or_create(
            name='ГрузоПеревозки',
            defaults={
                'description': 'Компания выполняет автомобильные грузоперевозки по Беларуси и соседним странам.',
                'address': 'г. Минск, ул. Логистическая, 10',
                'phone': '+375 (29) 111-22-33',
                'email': 'info@cargo.example',
                'founded_year': 2018,
                'requisites': 'УНП 123456789, р/с BY00TEST00000000000000000000',
            },
        )
        if not company.logo:
            company.logo.save('company-logo.png', self.make_image('Cargo', (45, 90, 130)), save=True)
        for year, event in (
            (2018, 'Основание компании.'),
            (2020, 'Расширение автопарка до 10 машин.'),
            (2024, 'Запуск личного кабинета клиента и водителя.'),
        ):
            CompanyHistory.objects.get_or_create(company=company, year=year, defaults={'event': event})

        body_types = [
            BodyType.objects.get_or_create(name=name, defaults={'description': desc})[0]
            for name, desc in (
                ('Тентованный', 'Для универсальных грузов.'),
                ('Рефрижератор', 'Для температурных грузов.'),
                ('Фургон', 'Закрытый кузов.'),
            )
        ]
        vehicle_types = [
            VehicleType.objects.get_or_create(name=name, defaults={'description': desc})[0]
            for name, desc in (
                ('Малотоннажный грузовик', 'Городские перевозки.'),
                ('Среднетоннажный грузовик', 'Региональные перевозки.'),
                ('Фура', 'Магистральные перевозки.'),
            )
        ]
        cargo_types = [
            CargoType.objects.get_or_create(name=name, defaults={'description': desc, 'is_hazardous': hazard})[0]
            for name, desc, hazard in (
                ('Мебель', 'Корпусная и мягкая мебель.', False),
                ('Продукты', 'Пищевые товары.', False),
                ('Стройматериалы', 'Сухие смеси, плитка, инструмент.', False),
                ('Химия', 'Бытовая химия и реагенты.', True),
            )
        ]
        services = [
            Service.objects.get_or_create(name=name, defaults={'price': Decimal(price), 'description': desc})[0]
            for name, price, desc in (
                ('Городская доставка', '80.00', 'Доставка груза в пределах города.'),
                ('Междугородняя перевозка', '250.00', 'Перевозка между городами.'),
                ('Погрузка', '45.00', 'Работа грузчиков при отправке.'),
                ('Разгрузка', '45.00', 'Работа грузчиков при получении.'),
                ('Страхование груза', '30.00', 'Дополнительная защита груза.'),
            )
        ]

        organization, _ = Organization.objects.get_or_create(
            name='ООО АльфаСклад',
            defaults={
                'address': 'г. Минск, ул. Складская, 5',
                'phone': '+375 (29) 222-33-44',
                'email': 'office@alpha.example',
                'contact_person': 'Иванов Иван',
            },
        )

        clients = []
        for index in range(1, 7):
            user, created = User.objects.get_or_create(
                username=f'client{index}',
                defaults={
                    'first_name': f'Клиент{index}',
                    'last_name': f'Тестовый{index}',
                    'email': f'client{index}@example.com',
                },
            )
            if created:
                user.set_password('client12345')
                user.save()
            client, _ = Client.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'birth_date': date(1990, 1, index),
                    'phone': f'+375 (29) 30{index}-10-10',
                    'email': user.email,
                    'address': f'г. Минск, ул. Клиентская, {index}',
                    'organization': organization if index % 2 == 0 else None,
                },
            )
            if not client.photo:
                client.photo.save(f'client-{index}.png', self.make_image(f'Client {index}', (90, 120, 160)), save=True)
            clients.append(client)

        drivers = []
        for index in range(1, 6):
            user, created = User.objects.get_or_create(
                username=f'driver{index}',
                defaults={
                    'first_name': f'Водитель{index}',
                    'last_name': f'Петров{index}',
                    'email': f'driver{index}@example.com',
                },
            )
            if created:
                user.set_password('driver12345')
                user.save()
            driver, _ = Driver.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'birth_date': date(1985, 2, index),
                    'phone': f'+375 (29) 40{index}-20-20',
                    'email': user.email,
                    'license_category': 'CE',
                    'license_number': f'AB{index}12345',
                    'experience_years': 3 + index,
                },
            )
            if not driver.photo:
                driver.photo.save(f'driver-{index}.png', self.make_image(f'Driver {index}', (60, 100, 150)), save=True)
            drivers.append(driver)

        vehicles = []
        for index, driver in enumerate(drivers, start=1):
            vehicle, _ = Vehicle.objects.get_or_create(
                plate_number=f'AB {1200 + index}-7',
                defaults={
                    'driver': driver,
                    'vehicle_type': vehicle_types[index % len(vehicle_types)],
                    'body_type': body_types[index % len(body_types)],
                    'brand': ['MAN', 'Volvo', 'Mercedes', 'DAF', 'Scania'][index - 1],
                    'model': f'Model {index}',
                    'year': 2018 + index,
                    'load_capacity_kg': 3000 * index,
                    'is_available': index % 2 == 1,
                },
            )
            if not vehicle.photo:
                vehicle.photo.save(f'vehicle-{index}.png', self.make_image(vehicle.brand, (80, 120, 80)), save=True)
            vehicles.append(vehicle)

        statuses = ['new', 'in_progress', 'delivered', 'cancelled']
        for index in range(1, 11):
            order, _ = Order.objects.get_or_create(
                origin=f'Минск, склад {index}',
                destination=f'Гомель, получатель {index}',
                client=clients[index % len(clients)],
                defaults={
                    'driver': drivers[index % len(drivers)],
                    'vehicle': vehicles[index % len(vehicles)],
                    'cargo_type': cargo_types[index % len(cargo_types)],
                    'distance_km': 250 + index,
                    'price': Decimal('300.00') + Decimal(index * 25),
                    'status': statuses[index % len(statuses)],
                },
            )
            order.services.set(services[: (index % len(services)) + 1])

        for index in range(1, 4):
            article, _ = Article.objects.get_or_create(
                title=f'Новость о перевозках {index}',
                defaults={
                    'summary': f'Краткая информация о новости {index}.',
                    'content': f'Полный текст новости о работе транспортной компании номер {index}.',
                    'is_published': True,
                },
            )
            if not article.image:
                article.image.save(f'article-{index}.png', self.make_image(f'News {index}', (120, 80, 120)), save=True)
            GlossaryTerm.objects.get_or_create(
                question=f'Термин {index}',
                defaults={'answer': f'Пояснение термина грузоперевозок номер {index}.'},
            )
            contact, _ = Contact.objects.get_or_create(
                full_name=f'Сотрудник {index}',
                defaults={
                    'position': ['Менеджер', 'Логист', 'Диспетчер'][index - 1],
                    'phone': f'+375 (29) 55{index}-30-30',
                    'email': f'employee{index}@cargo.example',
                    'description': 'Консультации клиентов и сопровождение заказов.',
                },
            )
            if not contact.photo:
                contact.photo.save(f'contact-{index}.png', self.make_image(f'Employee {index}', (130, 90, 60)), save=True)
            vacancy, _ = Vacancy.objects.get_or_create(
                title=['Водитель CE', 'Логист', 'Грузчик'][index - 1],
                defaults={
                    'description': 'Опыт работы приветствуется, оформление по договору.',
                    'salary': 'договорная',
                    'is_active': True,
                },
            )
            JobApplication.objects.get_or_create(
                vacancy=vacancy,
                user=clients[index].user,
                defaults={
                    'full_name': clients[index].get_full_name(),
                    'phone': clients[index].phone,
                    'email': clients[index].email,
                    'message': 'Готов обсудить условия работы.',
                    'status': ['pending', 'approved', 'rejected'][index - 1],
                },
            )
            Promo.objects.get_or_create(
                code=f'CARGO{index}0',
                defaults={
                    'discount_percent': index * 5,
                    'description': 'Скидка на перевозку.',
                    'valid_from': date.today() - timedelta(days=10),
                    'valid_to': date.today() + timedelta(days=30 * index),
                    'is_active': index < 3,
                },
            )
            Review.objects.get_or_create(
                user=clients[index].user,
                text=f'Хорошая работа службы перевозок, отзыв номер {index}.',
                defaults={'rating': 4 + (index % 2)},
            )

        self.stdout.write(self.style.SUCCESS('Демо-данные созданы. Суперпользователь: admin / admin12345'))
