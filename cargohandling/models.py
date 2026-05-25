import re
from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError

def validate_phone(value):
    pattern = r'^\+375\s*\(\d{2}\)\s*\d{3}-?\s?\d{2}-?\s?\s?\d{2}$'
    if not re.match(pattern, value):
        raise ValidationError('Формат: +375 (29) XXX-XX-XX')

def validate_adult(value):
    from datetime import date
    age = (date.today() - value).days // 365
    if age < 18:
        raise ValidationError('Возраст должен быть 18+')

class Organization(models.Model):
    name = models.CharField('Название организации', max_length=100)
    address = models.CharField("Адрес", max_length=300)
    phone = models.CharField('Телефон', max_length=20, validators=[validate_phone])
    email = models.EmailField('Email', blank=True)
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)
    contact_person = models.CharField('Контактное лицо', max_length=100, blank=True)

    class Meta:
        verbose_name = "Организация"

    def __str__(self):
        return self.name

class Person(models.Model):
    first_name = models.CharField('Имя', max_length=100)
    last_name = models.CharField('Фамилия', max_length=100)
    birth_date = models.DateField('Дата рождения', validators=[validate_adult])
    phone = models.CharField("Номер телефона", max_length=20, validators=[validate_phone])
    email = models.EmailField('Email', blank=True)
    photo = models.ImageField('Фото', upload_to='profiles/', blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def age(self):
        from datetime import date
        return (date.today() - self.birth_date).days // 365

    def get_full_name(self):
        return f'{self.last_name} {self.first_name}'.strip()


class Client(Person):
    user = models.OneToOneField(User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='client_profile')
    address = models.CharField('Адрес', max_length=300, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank = True)
    registered_at = models.DateTimeField('Дата регистрации', auto_now_add=True)

    def __str__(self):
        return f'{self.last_name} {self.first_name}'

class Driver(Person):
    user = models.OneToOneField(User,on_delete=models.CASCADE,  related_name='driver_profile')
    license_category = models.CharField('Категория', max_length=10, default='B')
    license_number = models.CharField('Номер ВУ', max_length=50)
    experience_years = models.PositiveIntegerField('Стаж, лет', default=0)
    hire_date = models.DateField('Дата приема', auto_now_add=True)
    is_available = models.BooleanField('Доступен', default=True)

    def __str__(self):
        return f'{self.last_name} {self.first_name}'

class CargoType(models.Model):
    name = models.CharField('Название груза', max_length=100)
    description = models.TextField('Описание', blank=True)
    is_hazardous = models.BooleanField('Опасный груз', default=False)
    class Meta:
        verbose_name = 'Вид груза'
        verbose_name_plural = 'Виды груза'
        ordering = ['name']

    def __str__(self):
        return self.name

class BodyType(models.Model):
    name = models.CharField('Тип кузова',max_length=100)
    description = models.TextField('Описание',blank=True)

    class Meta:
        verbose_name = 'Тип кузова'
        verbose_name_plural = 'Типы кузова'
        ordering = ['name']

    def __str__(self):
        return self.name

class VehicleType(models.Model):
    name = models.CharField('Вид транспортного средства',max_length=100)
    description = models.TextField('Описание',blank=True)

    class Meta:
        verbose_name = 'Вид транспортного средства'
        verbose_name_plural = 'Виды транспортных средств'
        ordering = ['name']

    def __str__(self):
        return self.name

class Vehicle(models.Model):
    driver = models.OneToOneField(Driver, on_delete=models.SET_NULL,null=True, blank=True,
            verbose_name='Водитель', related_name='vehicle')
    vehicle_type = models.ForeignKey(
        VehicleType,on_delete=models.SET_NULL,
        null=True,blank=True,verbose_name='Вид ТС')
    body_type = models.ForeignKey(BodyType,on_delete=models.SET_NULL,
        null=True,blank=True,verbose_name='Тип кузова')
    brand = models.CharField('Марка', max_length=100)
    model = models.CharField('Модель', max_length=100)
    plate_number = models.CharField('Гос. номер', max_length=20, unique=True)
    year = models.PositiveIntegerField('Год выпуска')
    load_capacity_kg = models.PositiveIntegerField('Грузоподъемность, кг')
    is_available = models.BooleanField('Свободна', default=True)
    photo = models.ImageField('Фото', upload_to='vehicles/', blank=True, null=True)

    class Meta:
        verbose_name = 'Транспортное средство'
        verbose_name_plural = 'Транспортные средства'
        ordering = ['brand', 'model', 'year']

    def __str__(self):
        return f'{self.brand} {self.model} ({self.plate_number})'

class Service(models.Model):
    name = models.CharField('Название услуги', max_length=200)
    price = models.DecimalField('Цена, руб.', max_digits=10, decimal_places=2)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — {self.price} руб.'


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'), ('in_progress', 'В пути'),
        ('delivered', 'Доставлен'), ('cancelled', 'Отменён'),
    ]

    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    cargo_type = models.ForeignKey(CargoType, on_delete=models.PROTECT)
    services = models.ManyToManyField(Service, blank=True)

    origin = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    distance_km = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

    def __str__(self):
        return f'Заказ #{self.pk} | {self.origin} → {self.destination}'

    def get_total_price(self):
        services_total = sum(s.price for s in self.services.all())
        return self.price + services_total


class Article(models.Model):
    title = models.CharField('Заголовок',max_length=200)
    summary = models.CharField('Краткое содержание',
        max_length=500,help_text='Одно предложение, которое видно в списке новостей')
    content = models.TextField('Полный текст статьи')
    image = models.ImageField('Картинка',upload_to='news/',
        blank=True,null=True)
    published_at = models.DateTimeField('Дата публикации',auto_now_add=True)
    is_published = models.BooleanField(
        'Опубликована',default=True,
        help_text='Снять галочку, чтобы скрыть новость')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-published_at']  # минус = свежие первые

    def __str__(self):
        return self.title


class GlossaryTerm(models.Model):
    question = models.CharField('Вопрос', max_length=300)
    answer = models.TextField('Ответ')
    added_at = models.DateTimeField('Дата обновления', auto_now_add=True)

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = 'Термин'
        verbose_name_plural = 'Словарь терминов'
        ordering = ['question']

class Contact(models.Model):
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    position = models.CharField('Должность',max_length=200)
    phone = models.CharField('Телефон',
        max_length=20,validators=[validate_phone],
        help_text='Формат: +375 (29) XXX-XX-XX'
    )
    email = models.EmailField('Email', blank=True)
    photo = models.ImageField('Фото',upload_to='contacts/',blank=True,null=True)
    description = models.TextField('Описание / обязанности',
        blank=True,help_text='Что делает сотрудник')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} — {self.position}'

class Vacancy(models.Model):
    title = models.CharField('Должность',max_length=200)
    description = models.TextField('Описание вакансии',
        help_text='Обязанности, требования, условия работы')
    salary = models.CharField('Зарплата',max_length=100,
        blank=True,help_text='Например: от 1500 руб. или договорная')
    is_active = models.BooleanField('Активна',default=True,
        help_text='Снять галочку, если вакансия закрыта')
    created_at = models.DateTimeField('Дата публикации',auto_now_add=True)

    class Meta:
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]

    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    full_name = models.CharField('ФИО', max_length=200)
    phone = models.CharField('Телефон', max_length=20, validators=[validate_phone])
    email = models.EmailField('Email', blank=True)
    message = models.TextField('Комментарий', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_comment = models.TextField('Комментарий администратора', blank=True)
    created_at = models.DateTimeField('Дата подачи', auto_now_add=True)
    updated_at = models.DateTimeField('Дата изменения', auto_now=True)

    class Meta:
        verbose_name = 'Заявка на вакансию'
        verbose_name_plural = 'Заявки на вакансии'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} — {self.vacancy}'


class Review(models.Model):
    RATING_CHOICES = [(1, '1 - Ужасно'),(2, '2 - Плохо'),(3, '3 - Нормально'),
                      (4, '4 - Хорошо'),(5, '5 - Отлично'),]

    user = models.ForeignKey(User,on_delete=models.CASCADE,
        verbose_name='Пользователь',related_name='reviews')
    rating = models.PositiveSmallIntegerField('Оценка',choices=RATING_CHOICES)
    text = models.TextField('Текст отзыва')
    created_at = models.DateTimeField('Дата',auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.rating}★'


class Promo(models.Model):
    code = models.CharField('Промокод',max_length=50,
        unique=True,help_text='Например: SUMMER2024')
    discount_percent = models.PositiveIntegerField('Скидка, %',
        help_text='Размер скидки в процентах (от 1 до 100)')
    description = models.CharField('Описание',max_length=200,
        blank=True,help_text='Например: Скидка на летние перевозки')
    valid_from = models.DateField('Действует с',
        help_text='Дата начала действия промокода')
    valid_to = models.DateField('Действует по',
        help_text='Дата окончания действия промокода')
    is_active = models.BooleanField('Активен',default=True,
        help_text='Отключите, чтобы временно заблокировать промокод')

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды и купоны'
        ordering = ['-valid_to']  # сначала те, у которых позже дата окончания

    def __str__(self):
        return f'{self.code} — {self.discount_percent}%'

    @property
    def is_expired(self):
        from datetime import date
        return date.today() > self.valid_to

    def clean(self):
        if self.discount_percent < 1 or self.discount_percent > 100:
            raise ValidationError({'discount_percent': 'Скидка должна быть от 1 до 100%.'})
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError({'valid_to': 'Дата окончания не может быть раньше даты начала.'})

class CompanyInfo(models.Model):
    name = models.CharField(
        'Название компании',max_length=200)
    description = models.TextField(
        'Описание компании',help_text='Основной текст о компании')
    logo = models.ImageField(
        'Логотип',upload_to='company/',blank=True,null=True)
    video_url = models.URLField(
    'Ссылка на видео',blank=True,help_text='YouTube или Vimeo ссылка')
    address = models.CharField('Адрес',max_length=300,blank=True)
    phone = models.CharField('Телефон',
        max_length=20,validators=[validate_phone],blank=True)
    email = models.EmailField('Email',blank=True)
    founded_year = models.PositiveIntegerField(
        'Год основания',null=True,blank=True)
    requisites = models.TextField('Реквизиты',
        blank=True,help_text='Банковские реквизиты, УНП и т.д.')

    class Meta:
        verbose_name = 'Информация о компании'
        verbose_name_plural = 'Информация о компании'

    def __str__(self):
        return self.name

class CompanyHistory(models.Model):
    company = models.ForeignKey(CompanyInfo,
        on_delete=models.CASCADE,verbose_name='Компания',related_name='history')
    year = models.PositiveIntegerField('Год')
    event = models.TextField(
        'Событие',help_text='Что произошло в этом году')

    class Meta:
        verbose_name = 'Событие истории'
        verbose_name_plural = 'История компании'
        ordering = ['year']

    def __str__(self):
        return f'{self.year}: {self.event[:50]}'
