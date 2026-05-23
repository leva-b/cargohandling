from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Driver, JobApplication, Client, Order, Review, validate_adult, validate_phone

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'client', 'driver', 'vehicle', 'cargo_type',
            'origin', 'destination', 'distance_km',
            'price', 'services', 'status',
        ]
        widgets = {
            'origin': forms.TextInput(attrs={
                'placeholder': 'Адрес отправления',
                'required': True,
                'maxlength': 200,
            }),
            'destination': forms.TextInput(attrs={
                'placeholder': 'Адрес назначения',
                'required': True,
                'maxlength': 200,
            }),
            'distance_km': forms.NumberInput(attrs={
                'min': 0,
                'required': True,
            }),
            'price': forms.NumberInput(attrs={
                'min': 0,
                'step': '0.01',
                'required': True,
            }),
            'services': forms.CheckboxSelectMultiple(),
            'status': forms.Select(),
            'client': forms.Select(),
            'driver': forms.Select(),
            'vehicle': forms.Select(),
            'cargo_type': forms.Select(),
        }
        labels = {
            'client': 'Клиент',
            'origin': 'Откуда',
            'destination': 'Куда',
            'distance_km': 'Расстояние, км',
            'price': 'Стоимость, руб.',
            'services': 'Дополнительные услуги',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not (user and user.is_superuser):
            self.fields.pop('client', None)

    def clean_distance_km(self):
        distance = self.cleaned_data.get('distance_km')
        if distance is not None and distance <= 0:
            raise ValidationError('Расстояние должно быть больше 0.')
        return distance

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise ValidationError('Цена не может быть отрицательной.')
        return price

    def clean(self):
        cleaned = super().clean()
        origin = cleaned.get('origin', '').strip()
        destination = cleaned.get('destination', '').strip()
        if origin and destination and origin.lower() == destination.lower():
            raise ValidationError('Адрес отправления и назначения не должны совпадать.')
        return cleaned

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(attrs={'required': True}),
            'text': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Напишите ваш отзыв...',
                'required': True,
                'minlength': 10,
            }),
        }
        labels = {
            'rating': 'Оценка',
            'text': 'Текст отзыва',
        }

    def clean_text(self):
        text = self.cleaned_data.get('text', '').strip()
        if len(text) < 10:
            raise ValidationError('Отзыв должен содержать не менее 10 символов.')
        return text


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {'status': forms.Select()}


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
        }


class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'birth_date', 'phone', 'email', 'address']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'phone': forms.TextInput(attrs={
                'placeholder': '+375 (29) 123-45-67',
                'pattern': r'^\+375\s\(\d{2}\)\s\d{3}-\d{2}-\d{2}$',
            }),
        }


class DriverProfileForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['first_name', 'last_name', 'birth_date', 'phone', 'email', 'photo', 'is_available']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'phone': forms.TextInput(attrs={
                'placeholder': '+375 (29) 123-45-67',
                'pattern': r'^\+375\s\(\d{2}\)\s\d{3}-\d{2}-\d{2}$',
            }),
        }


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['full_name', 'phone', 'email', 'message']
        widgets = {
            'phone': forms.TextInput(attrs={
                'placeholder': '+375 (29) 123-45-67',
                'pattern': r'^\+375\s\(\d{2}\)\s\d{3}-\d{2}-\d{2}$',
            }),
            'message': forms.Textarea(attrs={'rows': 4}),
        }


class JobApplicationDecisionForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['status', 'admin_comment']
        widgets = {
            'status': forms.Select(),
            'admin_comment': forms.Textarea(attrs={'rows': 3}),
        }

class RegisterForm(forms.Form):
    username = forms.CharField(
        label='Логин',
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Придумайте логин',
            'required': True,
            'maxlength': 150,
        }),
    )
    first_name = forms.CharField(
        label='Имя',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Имя',
            'required': True,
            'maxlength': 100,
        }),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Фамилия',
            'required': True,
            'maxlength': 100,
        }),
    )
    birth_date = forms.DateField(
        label='Дата рождения',
        validators=[validate_adult],
        widget=forms.DateInput(attrs={
            'type': 'date',
            'required': True,
        }),
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=20,
        validators=[validate_phone],
        widget=forms.TextInput(attrs={
            'placeholder': '+375 (29) 123-45-67',
            'pattern': r'^\+375\s\(\d{2}\)\s\d{3}-\d{2}-\d{2}$',
            'required': True,
            'maxlength': 20,
        }),
    )
    address = forms.CharField(
        label='Адрес',
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Адрес',
            'maxlength': 300,
        }),
    )
    email = forms.EmailField(
        label='Email',
        required=False,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email (необязательно)',
        }),
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Пароль',
            'required': True,
        }),
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите пароль',
            'required': True,
        }),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Пользователь с таким логином уже существует.')
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Пароли не совпадают.')
        return cleaned

    def save(self):
        """Создаёт и возвращает нового пользователя."""
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            password=data['password1'],
            email=data.get('email', ''),
            first_name=data['first_name'],
            last_name=data['last_name'],
        )
        Client.objects.create(
            user=user,
            first_name=data['first_name'],
            last_name=data['last_name'],
            birth_date=data['birth_date'],
            phone=data['phone'],
            email=data.get('email', ''),
            address=data.get('address', ''),
        )
        return user

class LoginForm(forms.Form):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'placeholder': 'Логин',
            'autofocus': True,
            'required': True,
        }),
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Пароль',
            'required': True,
        }),
    )
