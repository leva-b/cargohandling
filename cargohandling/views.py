import logging
import statistics as py_statistics
import os
from io import BytesIO

from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.db.models.functions import TruncDate

from .models import (
    Driver, Vehicle, Service, Article, Contact,
    Vacancy, Order, Review, Promo, GlossaryTerm,
    CompanyInfo, CargoType, Organization, Client, JobApplication,
)
from .forms import (
    ClientProfileForm, DriverProfileForm, JobApplicationDecisionForm,
    JobApplicationForm, OrderForm, OrderStatusForm, ReviewForm,
    RegisterForm, LoginForm, UserProfileForm,
)
from .external_apis import get_usd_byn_rate, get_world_time

from PIL import Image, ImageDraw, ImageFont


logger = logging.getLogger(__name__)

def _chart_font(size: int = 14):
    """
    PIL default bitmap font doesn't support Cyrillic, which results in "tofu" squares.
    Prefer a Windows TrueType font that supports Cyrillic; fallback to default if missing.
    """
    candidates = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\verdana.ttf",
    ]

    for path in candidates:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size=size)
        except Exception:
            # If freetype/font loading fails for any reason, try next candidate.
            continue

    return ImageFont.load_default()


def _get_client(user):
    try:
        return user.client_profile
    except Exception:
        return None


def _get_driver(user):
    try:
        return user.driver_profile
    except Exception:
        return None


def _orders_for_user(user):
    if user.is_superuser:
        return Order.objects.select_related('client', 'driver', 'vehicle', 'cargo_type')

    driver = _get_driver(user)
    if driver:
        return Order.objects.filter(driver=driver).select_related(
            'client', 'vehicle', 'cargo_type'
        )

    client = _get_client(user)
    if client:
        return Order.objects.filter(client=client).select_related(
            'driver', 'vehicle', 'cargo_type'
        )

    return Order.objects.none()

def index(request):
    """Главная: последняя опубликованная статья."""
    last_article = Article.objects.filter(is_published=True).first()
    world_time = get_world_time()
    currency_rate = get_usd_byn_rate()
    return render(request, 'cargohandling/pages/index.html', {
        'last_article': last_article,
        'world_time': world_time,
        'currency_rate': currency_rate,
    })

def about(request):
    company = CompanyInfo.objects.prefetch_related('history').first()
    return render(request, 'cargohandling/pages/about.html', {
        'company': company,
    })

def glossary(request):
    terms = GlossaryTerm.objects.all()
    return render(request, 'cargohandling/pages/glossary.html', {
        'terms': terms,
    })

def contacts(request):
    contacts_list = Contact.objects.all()
    return render(request, 'cargohandling/pages/contacts.html', {
        'contacts': contacts_list,
    })


def vacancies(request):
    vacancies_list = Vacancy.objects.filter(is_active=True)
    return render(request, 'cargohandling/pages/vacancies.html', {
        'vacancies': vacancies_list,
    })


@login_required
def vacancy_apply(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, is_active=True)
    initial = {
        'full_name': request.user.get_full_name() or request.user.username,
        'email': request.user.email,
    }
    client = _get_client(request.user)
    driver = _get_driver(request.user)
    if client:
        initial['phone'] = client.phone
    elif driver:
        initial['phone'] = driver.phone

    if request.method == 'POST':
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.vacancy = vacancy
            application.save()
            logger.info('Job application %s created by %s', application.pk, request.user.username)
            messages.success(request, 'Заявка отправлена.')
            return redirect('profile')
    else:
        form = JobApplicationForm(initial=initial)

    return render(request, 'cargohandling/pages/vacancy_apply.html', {
        'vacancy': vacancy,
        'form': form,
    })


def privacy(request):
    return render(request, 'cargohandling/pages/privacy.html')


def articles(request):
    articles_list = Article.objects.filter(is_published=True)
    return render(request, 'cargohandling/pages/articles.html', {
        'articles': articles_list,
    })


def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk, is_published=True)
    return render(request, 'cargohandling/pages/article_detail.html', {
        'article': article,
    })


def promos(request):
    """Промокоды: активные и архивные."""
    active = Promo.objects.filter(is_active=True)
    archived = Promo.objects.filter(is_active=False)
    return render(request, 'cargohandling/pages/promos.html', {
        'active': active,
        'archived': archived,
    })

def drivers(request):
    q = request.GET.get('q', '')
    sort = request.GET.get('sort', 'last_name')
    allowed_sorts = ('last_name', 'experience_years', '-experience_years')
    if sort not in allowed_sorts:
        sort = 'last_name'

    drivers_list = Driver.objects.select_related('vehicle')
    if q:
        drivers_list = drivers_list.filter(
            Q(last_name__icontains=q) | Q(first_name__icontains=q)
        )
    drivers_list = drivers_list.order_by(sort)

    return render(request, 'cargohandling/drivers/drivers.html', {
        'drivers': drivers_list,
        'q': q,
        'sort': sort,
    })


def driver_detail(request, driver_id):
    """Детальная страница водителя с привязанным ТС."""
    driver = get_object_or_404(Driver, pk=driver_id)
    return render(request, 'cargohandling/drivers/driver_detail.html', {
        'driver': driver,
    })

def vehicles(request):
    q = request.GET.get('q', '')
    available = request.GET.get('available', '')
    vehicles_list = Vehicle.objects.select_related('driver', 'vehicle_type', 'body_type')
    if q:
        vehicles_list = vehicles_list.filter(
            Q(brand__icontains=q) | Q(model__icontains=q)
        )
    if available == '1':
        vehicles_list = vehicles_list.filter(is_available=True)
    vehicles_list = vehicles_list.order_by('brand', 'model')

    return render(request, 'cargohandling/vehicles.html', {
        'vehicles': vehicles_list,
        'q': q,
        'available': available,
    })

def services(request):
    q = request.GET.get('q', '')
    sort = request.GET.get('sort', 'name')
    allowed_sorts = ('name', 'price', '-price')
    if sort not in allowed_sorts:
        sort = 'name'

    services_list = Service.objects.filter(is_active=True)
    if q:
        services_list = services_list.filter(name__icontains=q)
    services_list = services_list.order_by(sort)

    return render(request, 'cargohandling/services.html', {
        'services': services_list,
        'q': q,
        'sort': sort,
    })

def orders(request):
    if not request.user.is_authenticated:
        return redirect('login')

    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    orders_list = _orders_for_user(request.user)

    if q:
        orders_list = orders_list.filter(
            Q(origin__icontains=q) | Q(destination__icontains=q)
        )
    if status_filter:
        orders_list = orders_list.filter(status=status_filter)

    orders_list = orders_list.order_by('-created_at')

    return render(request, 'cargohandling/orders/orders.html', {
        'orders': orders_list,
        'q': q,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    })


def order_detail(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')

    order = get_object_or_404(Order, pk=pk)

    # Проверяем доступ
    client = _get_client(request.user)
    driver = _get_driver(request.user)
    has_access = (
        request.user.is_superuser
        or (client and order.client == client)
        or (driver and order.driver == driver)
    )
    if not has_access:
        messages.error(request, 'У вас нет доступа к этому заказу.')
        return redirect('orders')

    can_edit_order = request.user.is_superuser or (client and order.client == client)
    can_delete_order = request.user.is_superuser
    can_change_status = request.user.is_superuser or (driver and order.driver == driver)

    return render(request, 'cargohandling/orders/order_detail.html', {
        'order': order,
        'can_edit_order': can_edit_order,
        'can_delete_order': can_delete_order,
        'can_change_status': can_change_status,
    })


@login_required
def order_create(request):
    client = _get_client(request.user)
    if not client and not request.user.is_superuser:
        messages.error(request, 'Создавать заказы могут только клиенты.')
        return redirect('orders')

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            if client:
                order.client = client
            order.save()
            form.save_m2m()
            logger.info('Order %s created by %s', order.pk, request.user.username)
            messages.success(request, f'Заказ #{order.pk} успешно создан.')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm(user=request.user)

    return render(request, 'cargohandling/orders/order_form.html', {
        'form': form,
        'title': 'Новый заказ',
    })


@login_required
def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk)
    client = _get_client(request.user)

    if not request.user.is_superuser and (not client or order.client != client):
        messages.error(request, 'Нет прав для редактирования этого заказа.')
        return redirect('orders')

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order, user=request.user)
        if form.is_valid():
            form.save()
            logger.info('Order %s updated by %s', order.pk, request.user.username)
            messages.success(request, f'Заказ #{order.pk} обновлён.')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm(instance=order, user=request.user)

    return render(request, 'cargohandling/orders/order_form.html', {
        'form': form,
        'title': f'Редактировать заказ #{order.pk}',
        'order': order,
    })


@login_required
def order_status_edit(request, pk):
    order = get_object_or_404(Order, pk=pk)
    driver = _get_driver(request.user)
    if not request.user.is_superuser and (not driver or order.driver != driver):
        messages.error(request, 'Статус этого заказа может менять только назначенный водитель или администратор.')
        return redirect('order_detail', pk=order.pk)

    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            logger.info('Order %s status changed to %s by %s', order.pk, order.status, request.user.username)
            messages.success(request, 'Статус заказа обновлён.')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderStatusForm(instance=order)

    return render(request, 'cargohandling/orders/order_status_form.html', {
        'order': order,
        'form': form,
    })


@login_required
def order_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Удалять заказы может только администратор.')
        return redirect('orders')

    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.delete()
        logger.info('Order %s deleted by %s', pk, request.user.username)
        messages.success(request, f'Заказ #{pk} удалён.')
        return redirect('orders')

    return render(request, 'cargohandling/orders/orders_confirm_delete.html', {
        'order': order,
    })


def reviews(request):
    reviews_list = Review.objects.select_related('user').order_by('-created_at')

    form = None
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.user = request.user
                review.save()
                messages.success(request, 'Отзыв добавлен!')
                return redirect('reviews')
        else:
            form = ReviewForm()

    return render(request, 'cargohandling/pages/reviews.html', {
        'reviews': reviews_list,
        'form': form,
    })

@login_required
def profile(request):
    driver = _get_driver(request.user)
    client = _get_client(request.user)

    context = {
        'user_form': UserProfileForm(instance=request.user),
        'client_form': ClientProfileForm(instance=client) if client else None,
        'driver_form': DriverProfileForm(instance=driver) if driver else None,
        'job_applications': JobApplication.objects.filter(user=request.user).select_related('vacancy'),
    }

    if request.user.is_superuser:
        context['all_job_applications'] = JobApplication.objects.select_related(
            'vacancy', 'user'
        ).order_by('-created_at')
        context['decision_forms'] = {
            application.pk: JobApplicationDecisionForm(instance=application)
            for application in context['all_job_applications']
        }

    if driver:
        driver_orders = Order.objects.filter(driver=driver).select_related(
            'client', 'cargo_type', 'vehicle'
        ).order_by('-created_at')
        context['driver'] = driver
        context['driver_orders'] = driver_orders

    if client:
        client_orders = Order.objects.filter(client=client).select_related(
            'driver', 'cargo_type', 'vehicle'
        ).prefetch_related('services').order_by('-created_at')
        active_promos = Promo.objects.filter(
            is_active=True,
            valid_to__gte=timezone.now().date()
        )
        context['client'] = client
        context['client_orders'] = client_orders
        context['active_promos'] = active_promos

    return render(request, 'cargohandling/pages/profile.html', context)


@login_required
def profile_edit(request):
    driver = _get_driver(request.user)
    client = _get_client(request.user)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        client_form = ClientProfileForm(request.POST, request.FILES, instance=client) if client else None
        driver_form = DriverProfileForm(request.POST, request.FILES, instance=driver) if driver else None

        forms = [user_form]
        if client_form:
            forms.append(client_form)
        if driver_form:
            forms.append(driver_form)

        if all(form.is_valid() for form in forms):
            user_form.save()
            if client_form:
                client_form.save()
            if driver_form:
                driver_form.save()
            logger.info('Profile updated by %s', request.user.username)
            messages.success(request, 'Личный кабинет обновлён.')
            return redirect('profile')
    else:
        user_form = UserProfileForm(instance=request.user)
        client_form = ClientProfileForm(instance=client) if client else None
        driver_form = DriverProfileForm(instance=driver) if driver else None

    return render(request, 'cargohandling/pages/profile_edit.html', {
        'user_form': user_form,
        'client_form': client_form,
        'driver_form': driver_form,
    })


@login_required
def job_application_decide(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Рассматривать заявки может только администратор.')
        return redirect('profile')

    application = get_object_or_404(JobApplication, pk=pk)
    if request.method == 'POST':
        form = JobApplicationDecisionForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            logger.info(
                'Job application %s changed to %s by %s',
                application.pk,
                application.status,
                request.user.username,
            )
            messages.success(request, 'Статус заявки обновлён.')
    return redirect('profile')

@login_required
def statistics(request):
    if not request.user.is_superuser:
        messages.error(request, 'Доступ только для администратора.')
        return redirect('index')

    clients = Client.objects.select_related('user', 'organization').order_by(
        'last_name', 'first_name'
    )

    # Сумма заказов по каждому клиенту
    clients_with_total = []
    for c in clients:
        total = Order.objects.filter(client=c).aggregate(
            total=Sum('price')
        )['total'] or 0
        clients_with_total.append({'client': c, 'total': total})

    # Общая сумма всех заказов
    total_revenue = Order.objects.aggregate(total=Sum('price'))['total'] or 0

    avg_price = Order.objects.aggregate(avg=Avg('price'))['avg'] or 0

    status_stats = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    popular_cargo = (
        Order.objects.values('cargo_type__name')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )

    client_ages = [c.age for c in clients if c.birth_date]
    avg_client_age = round(sum(client_ages) / len(client_ages), 1) if client_ages else 0
    median_client_age = py_statistics.median(client_ages) if client_ages else 0

    drivers_all = Driver.objects.all()
    driver_ages = [d.age for d in drivers_all if d.birth_date]
    avg_driver_age = round(sum(driver_ages) / len(driver_ages), 1) if driver_ages else 0
    median_driver_age = py_statistics.median(driver_ages) if driver_ages else 0

    order_prices = [float(price) for price in Order.objects.values_list('price', flat=True)]
    median_price = round(py_statistics.median(order_prices), 2) if order_prices else 0
    try:
        mode_price = py_statistics.mode(order_prices) if order_prices else 0
    except py_statistics.StatisticsError:
        mode_price = 0

    total_orders = Order.objects.count()
    status_choices = dict(Order.STATUS_CHOICES)
    status_rows = []
    max_status_count = max([item['count'] for item in status_stats], default=1)
    for item in status_stats:
        status_rows.append({
            'code': item['status'],
            'name': status_choices.get(item['status'], item['status']),
            'count': item['count'],
            'bar': '#' * max(1, round(item['count'] / max_status_count * 30)),
        })

    return render(request, 'cargohandling/pages/statistics.html', {
        'clients_with_total': clients_with_total,
        'total_revenue': total_revenue,
        'avg_price': round(avg_price, 2),
        'median_price': median_price,
        'mode_price': mode_price,
        'status_rows': status_rows,
        'popular_cargo': popular_cargo,
        'avg_client_age': avg_client_age,
        'median_client_age': median_client_age,
        'avg_driver_age': avg_driver_age,
        'median_driver_age': median_driver_age,
        'total_orders': total_orders,
    })


@login_required
def statistics_status_chart(request):

    if not request.user.is_superuser:
        messages.error(request, 'Доступ только для администратора.')
        return redirect('index')

    status_stats = (
        Order.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    status_choices = dict(Order.STATUS_CHOICES)

    labels = [status_choices.get(item['status'], item['status']) for item in status_stats]
    values = [int(item['count']) for item in status_stats]
    max_value = max(values) if values else 1

    width, height = 900, 420
    padding = 40
    chart_height = height - padding * 2
    chart_width = width - padding * 2

    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = _chart_font(14)

    draw.line((padding, padding, padding, height - padding), fill=(0, 0, 0), width=2)
    draw.line((padding, height - padding, width - padding, height - padding), fill=(0, 0, 0), width=2)

    bar_count = max(len(values), 1)
    gap = 16
    bar_width = max(20, (chart_width - gap * (bar_count + 1)) // bar_count)

    x = padding + gap
    for label, value in zip(labels, values):
        bar_h = int((value / max_value) * (chart_height - 20))
        y0 = height - padding
        y1 = y0 - bar_h

        draw.rectangle((x, y1, x + bar_width, y0), outline=(0, 0, 0), fill=(120, 160, 220), width=2)
        draw.text((x, y1 - 14), str(value), fill=(0, 0, 0), font=font)

        # label (truncate to fit)
        short = label if len(label) <= 14 else (label[:13] + '.')
        draw.text((x, y0 + 6), short, fill=(0, 0, 0), font=font)

        x += bar_width + gap

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required
def statistics_orders_over_time_chart(request):
    if not request.user.is_superuser:
        messages.error(request, 'Доступ только для администратора.')
        return redirect('index')

    today = timezone.now().date()
    start = today - timezone.timedelta(days=13)

    rows = (
        Order.objects.filter(created_at__date__gte=start, created_at__date__lte=today)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    counts_by_day = {row['day']: int(row['count']) for row in rows}
    days = [start + timezone.timedelta(days=i) for i in range(14)]
    values = [counts_by_day.get(day, 0) for day in days]
    max_value = max(values) if values else 1

    width, height = 900, 360
    padding = 50
    chart_height = height - padding * 2
    chart_width = width - padding * 2

    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = _chart_font(14)

    # axes
    draw.line((padding, padding, padding, height - padding), fill=(0, 0, 0), width=2)
    draw.line((padding, height - padding, width - padding, height - padding), fill=(0, 0, 0), width=2)

    # points
    step_x = chart_width / max(13, 1)
    points = []
    for i, value in enumerate(values):
        x = padding + i * step_x
        y = height - padding - (value / max_value) * (chart_height - 10)
        points.append((x, y))

    # line
    if len(points) >= 2:
        draw.line(points, fill=(30, 120, 80), width=3)

    # markers + labels (every 2 days)
    for i, ((x, y), day, value) in enumerate(zip(points, days, values)):
        r = 4
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(30, 120, 80), outline=(0, 0, 0))
        if i % 2 == 0:
            draw.text((x - 18, height - padding + 8), day.strftime('%d/%m'), fill=(0, 0, 0), font=font)
        if i in (0, len(points) - 1):
            draw.text((x - 6, y - 16), str(value), fill=(0, 0, 0), font=font)

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            logger.info('User %s registered as client', user.username)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('profile')
    else:
        form = RegisterForm()

    return render(request, 'cargohandling/auth/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                next_url = request.GET.get('next', 'index')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверный логин или пароль.')
    else:
        form = LoginForm()

    return render(request, 'cargohandling/auth/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('index')


@login_required
def orders_api(request):
    orders_list = _orders_for_user(request.user).prefetch_related('services').order_by('-created_at')
    data = []
    for order in orders_list:
        data.append({
            'id': order.pk,
            'origin': order.origin,
            'destination': order.destination,
            'status': order.status,
            'status_display': order.get_status_display(),
            'client': str(order.client),
            'driver': str(order.driver) if order.driver else None,
            'vehicle': str(order.vehicle) if order.vehicle else None,
            'cargo_type': str(order.cargo_type),
            'price': str(order.price),
            'total_price': str(order.get_total_price()),
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'services': [service.name for service in order.services.all()],
        })
    return JsonResponse({'orders': data})
