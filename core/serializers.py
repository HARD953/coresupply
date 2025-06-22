from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import *

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 
            'username', 
            'email', 
            'password',
            'first_name', 
            'last_name',
            'user_type',
            'phone_number',
            'is_verified',
            'token_balance',
            'date_joined'
        ]
        read_only_fields = ['is_verified', 'token_balance', 'date_joined']
    
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        extra_kwargs = {
            'user': {'required': False}  # On rend le champ user optionnel en écriture
        }

    def create(self, validated_data):
        # Ajoute automatiquement l'utilisateur connecté
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class RetailPointSerializer(serializers.ModelSerializer):
    address = AddressSerializer()
    
    class Meta:
        model = RetailPoint
        fields = [
            'id',
            'owner',
            'name',
            'description',
            'retail_point_type',
            'address',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        address_data = validated_data.pop('address')
        address = Address.objects.create(**address_data)
        return RetailPoint.objects.create(address=address, **validated_data)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFormat
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    formats = ProductFormatSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('manufacturer',)

    def validate(self, data):
        # Vérifier que l'utilisateur est un fabricant
        if self.context['request'].user.user_type != 'MANUFACTURER':
            raise serializers.ValidationError("Seuls les fabricants peuvent créer des produits")
        return data

    def create(self, validated_data):
        # Associer automatiquement le fabricant
        validated_data['manufacturer'] = self.context['request'].user
        return super().create(validated_data)


class InventorySerializer(serializers.ModelSerializer):
    product_format = ProductFormatSerializer(read_only=True)
    product_format_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductFormat.objects.all(),
        source='product_format',
        write_only=True
    )
    retail_point = serializers.StringRelatedField(read_only=True)
    retail_point_id = serializers.PrimaryKeyRelatedField(
        queryset=RetailPoint.objects.filter(is_active=True),
        source='retail_point',
        write_only=True
    )

    class Meta:
        model = Inventory
        fields = '__all__'
        read_only_fields = ('last_updated',)

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at')

    def validate(self, data):
        # Validation supplémentaire pour les sorties de stock
        if data['movement_type'] == 'OUT':
            inventory = data['inventory']
            if inventory.current_stock < data['quantity']:
                raise serializers.ValidationError(
                    f"Stock insuffisant. Stock actuel: {inventory.current_stock}"
                )
        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CartItemSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(read_only=True)
    inventory_id = serializers.PrimaryKeyRelatedField(
        queryset=Inventory.objects.filter(is_available=True),
        source='inventory',
        write_only=True
    )

    class Meta:
        model = CartItem
        fields = '__all__'
        read_only_fields = ('added_at', 'cart')

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ('unit_price', 'total_price')

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('user', 'order_number', 'total_amount', 'created_at', 'updated_at')

    def validate(self, data):
        if self.instance and self.instance.status not in ['DRAFT', 'PENDING']:
            raise serializers.ValidationError("Seules les commandes brouillon ou en attente peuvent être modifiées")
        return data


class TokenTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenTransaction
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('user', 'created_at')


class DisputeMessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = DisputeMessage
        fields = '__all__'
        read_only_fields = ('created_at', 'sender')

class DisputeSerializer(serializers.ModelSerializer):
    messages = DisputeMessageSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    assigned_to = serializers.StringRelatedField(read_only=True)
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = Dispute
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'status')

    def validate(self, data):
        user = self.context['request'].user
        order = data.get('order')

        if order and order.user != user:
            raise serializers.ValidationError("Vous ne pouvez créer un litige que pour vos propres commandes")
        
        return data


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at', 'file')

class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')

    def validate(self, data):
        if data.get('is_default', False):
            Dashboard.objects.filter(user=self.context['request'].user, is_default=True).update(is_default=False)
        return data


# core/serializers.py
class BulkProductUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(required=False)
    is_active = serializers.BooleanField(required=False)
    # Ajouter tous les champs modifiables

class RetailPointMapSerializer(serializers.ModelSerializer):
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    region = serializers.CharField(source='address.region')

    class Meta:
        model = RetailPoint
        fields = ['id', 'name', 'lat', 'lng', 'region']

    def get_lat(self, obj):
        coords = obj.address.gps_coordinates
        return float(coords.split(',')[0].strip()) if coords else None

    def get_lng(self, obj):
        coords = obj.address.gps_coordinates
        return float(coords.split(',')[1].strip()) if coords else None


class RetailPointMapSerializer(serializers.ModelSerializer):
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = RetailPoint
        fields = ['id', 'name', 'lat', 'lng']

    def get_lat(self, obj):
        return obj.address.gps_coordinates.split(',')[0] if obj.address.gps_coordinates else None

    def get_lng(self, obj):
        return obj.address.gps_coordinates.split(',')[1] if obj.address.gps_coordinates else None