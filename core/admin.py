from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Inventory)
admin.site.register(User)
admin.site.register(Address)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Product)
admin.site.register(ProductFormat)
admin.site.register(ProductImage)
admin.site.register(RetailPoint)
admin.site.register(StockMovement)
admin.site.register(CartItem)
admin.site.register(TokenTransaction)
admin.site.register(Notification)
admin.site.register(Category)
admin.site.register(Report)
admin.site.register(Dashboard)