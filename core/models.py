from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_TYPES = (
        ('INDIVIDUAL', 'Particulier'),
        ('RETAILER', 'Détaillant'),
        ('WHOLESALER', 'Grossiste'),
        ('SEMI_WHOLESALER', 'Demi-grossiste'),
        ('MANUFACTURER', 'Fabricant'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone_number = models.CharField(max_length=20)
    is_verified = models.BooleanField(default=False)
    token_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    district = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    commune = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    gps_coordinates = models.CharField(max_length=50, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

class RetailPoint(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    retail_point_type = models.CharField(max_length=50)  # boutique, supermarché, etc.
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    manufacturer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'MANUFACTURER'})
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ProductFormat(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='formats')
    name = models.CharField(max_length=100)  # Ex: "Pack de 6", "1L", "500g"
    sku = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=50, blank=True, null=True)
    unit_of_measure = models.CharField(max_length=20)  # Ex: "unit", "kg", "L"
    quantity_per_unit = models.DecimalField(max_digits=10, decimal_places=3)  # Ex: 6 pour un pack de 6
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    format = models.ForeignKey(ProductFormat, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"

class Inventory(models.Model):
    product_format = models.ForeignKey(ProductFormat, on_delete=models.CASCADE)
    retail_point = models.ForeignKey(RetailPoint, on_delete=models.CASCADE)
    current_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    alert_threshold = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product_format', 'retail_point')
        verbose_name_plural = 'Inventories'

    def __str__(self):
        return f"{self.product_format} at {self.retail_point}"

class StockMovement(models.Model):
    MOVEMENT_TYPES = (
        ('IN', 'Entrée de stock'),
        ('OUT', 'Sortie de stock'),
        ('ADJ', 'Ajustement'),
        ('TRF', 'Transfert'),
    )

    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    reference = models.CharField(max_length=100, blank=True, null=True)  # N° de commande, etc.
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_movement_type_display()} of {self.quantity} for {self.inventory}"

    def save(self, *args, **kwargs):
        # Mise à jour automatique du stock
        super().save(*args, **kwargs)
        self.update_inventory_stock()

    def update_inventory_stock(self):
        inventory = self.inventory
        if self.movement_type == 'IN':
            inventory.current_stock += self.quantity
        elif self.movement_type == 'OUT':
            inventory.current_stock -= self.quantity
        elif self.movement_type == 'ADJ':
            inventory.current_stock = self.quantity
        
        inventory.save()


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Panier de {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'inventory')

    def __str__(self):
        return f"{self.quantity}x {self.inventory}"

class Order(models.Model):
    ORDER_STATUS = (
        ('DRAFT', 'Brouillon'),
        ('PENDING', 'En attente'),
        ('CONFIRMED', 'Confirmée'),
        ('PROCESSING', 'En traitement'),
        ('SHIPPED', 'Expédiée'),
        ('DELIVERED', 'Livrée'),
        ('CANCELLED', 'Annulée'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    retail_point = models.ForeignKey(RetailPoint, on_delete=models.SET_NULL, null=True, blank=True)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='DRAFT')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Commande #{self.order_number}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.inventory}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class TokenTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Dépôt'),
        ('WITHDRAWAL', 'Retrait'),
        ('ORDER_PAYMENT', 'Paiement commande'),
        ('REFUND', 'Remboursement'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('ORDER_UPDATE', 'Mise à jour commande'),
        ('STOCK_ALERT', 'Alerte stock'),
        ('PAYMENT_CONFIRMATION', 'Confirmation paiement'),
        ('DISPUTE_UPDATE', 'Mise à jour litige'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Dispute(models.Model):
    DISPUTE_TYPES = (
        ('ORDER', 'Problème de commande'),
        ('DELIVERY', 'Problème de livraison'),
        ('PAYMENT', 'Problème de paiement'),
        ('PRODUCT', 'Problème produit'),
    )
    
    STATUS_CHOICES = (
        ('OPEN', 'Ouvert'),
        ('IN_REVIEW', 'En examen'),
        ('RESOLVED', 'Résolu'),
        ('REJECTED', 'Rejeté'),
    )

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_created')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    dispute_type = models.CharField(max_length=20, choices=DISPUTE_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class DisputeMessage(models.Model):
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    attachments = models.FileField(upload_to='disputes/attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class Report(models.Model):
    REPORT_TYPES = (
        ('SALES', 'Analyse des ventes'),
        ('STOCK', 'Analyse des stocks'),
        ('DISPUTES', 'Analyse des litiges'),
        ('USER', 'Analyse utilisateurs'),
    )

    REPORT_FORMATS = (
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
    )

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    filters = models.JSONField(default=dict)  # Pour stocker les paramètres du rapport
    format = models.CharField(max_length=10, choices=REPORT_FORMATS, default='PDF')
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Dashboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    widgets = models.JSONField()  # Configuration des widgets
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)