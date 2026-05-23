from django.contrib import admin

from .models import (
    BodyType, VehicleType, CargoType, Service,
    Driver, Vehicle, Organization, Client,
    Order,
    Article, GlossaryTerm, Contact, Vacancy,
    Review, Promo, CompanyInfo, CompanyHistory,
    JobApplication,
)

class CompanyHistoryInline(admin.TabularInline):
    model = CompanyHistory
    extra = 1          # сколько пустых строк показывать для добавления
    fields = ('year', 'event')


class VehicleInline(admin.StackedInline):
    model = Vehicle
    extra = 0
    fields = ('vehicle_type', 'body_type', 'brand', 'model', 'plate_number',
              'year', 'load_capacity_kg', 'is_available')
    can_delete = False


@admin.register(BodyType)
class BodyTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description',)
    search_fields = ('name',)

@admin.register(CargoType)
class CargoTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_hazardous')
    list_filter = ('is_hazardous',)
    search_fields = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('price', 'is_active')   # редактирование прямо в списке

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    # Inline: ТС водителя видно прямо в карточке водителя
    inlines = [VehicleInline]

    list_display = (
        'get_full_name', 'phone', 'license_category',
        'experience_years', 'is_available', 'age_display',
    )
    list_filter = ('is_available', 'license_category')
    search_fields = ('last_name', 'first_name', 'phone', 'license_number')
    readonly_fields = ('hire_date',)

    fieldsets = (
        ('Личные данные', {
            'fields': ('user', 'last_name', 'first_name',
                       'birth_date', 'phone', 'email', 'photo')
        }),
        ('Профессиональные данные', {
            'fields': ('license_number', 'license_category',
                       'experience_years', 'is_available', 'hire_date')
        }),
    )

    @admin.display(description='ФИО')
    def get_full_name(self, obj):
        return obj.get_full_name()

    @admin.display(description='Возраст')
    def age_display(self, obj):
        return f'{obj.age} лет'


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        '__str__', 'vehicle_type', 'driver',
        'load_capacity_kg', 'year', 'is_available',
    )
    list_filter = ('vehicle_type', 'is_available', 'year')
    search_fields = ('brand', 'model', 'plate_number')
    list_editable = ('is_available',)
    autocomplete_fields = ('driver', 'vehicle_type')


# ─────────────────────────────────────────────────────────────
# КЛИЕНТЫ И ОРГАНИЗАЦИИ
# ─────────────────────────────────────────────────────────────

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'contact_person', 'created_at')
    search_fields = ('name', 'phone', 'contact_person',)
    readonly_fields = ('created_at',)
    list_filter = ('created_at',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'get_full_name', 'phone', 'email',
        'organization', 'age_display', 'registered_at',
    )
    list_filter = ('organization',)
    search_fields = ('last_name', 'first_name', 'phone', 'email')
    readonly_fields = ('registered_at',)
    autocomplete_fields = ('organization',)

    @admin.display(description='ФИО')
    def get_full_name(self, obj):
        return obj.get_full_name()

    @admin.display(description='Возраст')
    def age_display(self, obj):
        return f'{obj.age} лет'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id','client','driver','origin','destination','status','price','created_at','updated_at',)
    list_filter = ('status', 'cargo_type')
    search_fields = ('client__last_name','client__first_name','origin','destination',)
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('services',)

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'summary')
    list_editable = ('is_published',)
    readonly_fields = ('published_at',)


@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ('question', 'added_at')
    search_fields = ('question', 'answer')
    readonly_fields = ('added_at',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'phone', 'email')
    search_fields = ('full_name', 'position', 'phone')


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'salary', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title',)
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'vacancy', 'user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'vacancy')
    search_fields = ('full_name', 'phone', 'email', 'user__username', 'vacancy__title')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'created_at', 'short_text')
    list_filter = ('rating',)
    search_fields = ('user__username', 'text')
    readonly_fields = ('created_at',)

    @admin.display(description='Текст')
    def short_text(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text


@admin.register(Promo)
class PromoAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_percent', 'valid_from',
        'valid_to', 'is_active', 'expired_display',
    )
    list_filter = ('is_active',)
    search_fields = ('code',)
    list_editable = ('is_active',)

    @admin.display(description='Истёк?', boolean=True)
    def expired_display(self, obj):
        return obj.is_expired


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    # История компании редактируется прямо здесь
    inlines = [CompanyHistoryInline]
    list_display = ('name', 'founded_year', 'phone', 'email')
