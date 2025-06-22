import django_filters
from .models import Order

class OrderFilter(django_filters.FilterSet):
    date_range = django_filters.DateFromToRangeFilter(field_name='created_at')
    min_amount = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')

    class Meta:
        model = Order
        fields = ['status', 'user__user_type']