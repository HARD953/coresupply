from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from rest_framework import viewsets  # Ajoutez cette ligne
from rest_framework.decorators import action
from rest_framework.views import APIView
from django_filters import FilterSet, DateFromToRangeFilter
from rest_framework.permissions import IsAdminUser
class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class AddressListView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        # Passe la requête au sérialiseur
        return {'request': self.request}

class RetailPointCreateView(generics.CreateAPIView):
    queryset = RetailPoint.objects.all()
    serializer_class = RetailPointSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['category', 'manufacturer']

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        
        # Filtrage par géolocalisation (à implémenter plus tard)
        if 'near' in self.request.query_params:
            # TODO: Implémenter la logique de filtrage par proximité
            pass
            
        return queryset

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

class ProductFormatCreateView(generics.CreateAPIView):
    queryset = ProductFormat.objects.all()
    serializer_class = ProductFormatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_id')
        product = get_object_or_404(Product, pk=product_id)
        
        # Vérifier que l'utilisateur est le fabricant du produit
        if product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas autorisé à ajouter des formats à ce produit")
            
        serializer.save(product=product)

class InventoryListView(generics.ListCreateAPIView):
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['retail_point', 'product_format__product']

    def get_queryset(self):
        user = self.request.user
        
        # Pour les fabricants: voir leurs produits chez tous les détaillants
        if user.user_type == 'MANUFACTURER':
            return Inventory.objects.filter(
                product_format__product__manufacturer=user
            ).select_related('product_format', 'retail_point')
        
        # Pour les détaillants/grossistes: voir leurs propres stocks
        elif user.user_type in ['RETAILER', 'WHOLESALER', 'SEMI_WHOLESALER']:
            return Inventory.objects.filter(
                retail_point__owner=user
            ).select_related('product_format', 'retail_point')
        
        # Pour les particuliers: seulement les stocks disponibles
        else:
            return Inventory.objects.filter(
                is_available=True,
                current_stock__gt=0
            ).select_related('product_format', 'retail_point')

class InventoryDetailView(generics.RetrieveUpdateAPIView):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'MANUFACTURER':
            return Inventory.objects.filter(
                product_format__product__manufacturer=user
            )
        else:
            return Inventory.objects.filter(
                retail_point__owner=user
            )

class StockMovementCreateView(generics.CreateAPIView):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class RetailPointInventoryView(generics.ListAPIView):
    serializer_class = InventorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        retail_point_id = self.kwargs['retail_point_id']
        return Inventory.objects.filter(
            retail_point_id=retail_point_id,
            is_available=True
        ).select_related('product_format')

class CartView(generics.RetrieveUpdateAPIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

class CartItemView(generics.CreateAPIView, generics.DestroyAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_create(self, serializer):
        cart = Cart.objects.get(user=self.request.user)
        serializer.save(cart=cart)

class OrderListView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'retail_point']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['RETAILER', 'WHOLESALER', 'SEMI_WHOLESALER']:
            # Pour les vendeurs: voir les commandes passées à eux
            return Order.objects.filter(
                items__inventory__retail_point__owner=user
            ).distinct()
        else:
            # Pour les acheteurs: voir leurs propres commandes
            return Order.objects.filter(user=user)

    def perform_create(self, serializer):
        # Logique de création de commande depuis le panier
        cart = Cart.objects.get(user=self.request.user)
        if not cart.items.exists():
            raise ValidationError("Le panier est vide")

        with transaction.atomic():
            order = serializer.save(
                user=self.request.user,
                status='PENDING',
                total_amount=0
            )
            
            total_amount = 0
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    inventory=item.inventory,
                    quantity=item.quantity,
                    unit_price=item.inventory.price_override or item.inventory.product_format.base_price,
                    total_price=item.quantity * (item.inventory.price_override or item.inventory.product_format.base_price)
                )
                total_amount += item.quantity * (item.inventory.price_override or item.inventory.product_format.base_price)
                
                # Mise à jour du stock
                StockMovement.objects.create(
                    inventory=item.inventory,
                    movement_type='OUT',
                    quantity=item.quantity,
                    reference=f"Commande #{order.order_number}",
                    created_by=self.request.user
                )
            
            order.total_amount = total_amount
            order.save()
            cart.items.all().delete()

class OrderDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['RETAILER', 'WHOLESALER', 'SEMI_WHOLESALER']:
            return Order.objects.filter(
                items__inventory__retail_point__owner=user
            ).distinct()
        else:
            return Order.objects.filter(user=user)


class TokenTransactionView(generics.ListCreateAPIView):
    serializer_class = TokenTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TokenTransaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        amount = serializer.validated_data['amount']
        
        with transaction.atomic():
            if serializer.validated_data['transaction_type'] == 'DEPOSIT':
                user.token_balance += amount
            elif serializer.validated_data['transaction_type'] == 'WITHDRAWAL':
                if user.token_balance < amount:
                    raise serializers.ValidationError("Solde insuffisant")
                user.token_balance -= amount
            
            user.save()
            serializer.save(user=user)

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class MarkNotificationAsReadView(generics.UpdateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch']

    def perform_update(self, serializer):
        serializer.save(is_read=True)


class ProductFormatListView(generics.ListAPIView):
    queryset = ProductFormat.objects.all()
    serializer_class = ProductFormatSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['product', 'is_active']

class ProductFormatDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductFormat.objects.all()
    serializer_class = ProductFormatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        product_format = self.get_object()
        if product_format.product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas le fabricant de ce produit")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas le fabricant de ce produit")
        instance.delete()

class ProductFormatListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductFormatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductFormat.objects.filter(product_id=product_id)

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']
        product = get_object_or_404(Product, pk=product_id)
        
        if product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas le fabricant de ce produit")
            
        serializer.save(product=product)


from rest_framework.parsers import MultiPartParser, FormParser

class ProductImageListView(generics.ListAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.AllowAny]

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_update(self, serializer):
        image = self.get_object()
        if image.product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas autorisé à modifier cette image")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas autorisé à supprimer cette image")
        instance.delete()

class ProductImageListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductImage.objects.filter(product_id=product_id)

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']
        product = get_object_or_404(Product, pk=product_id)
        
        if product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas le fabricant de ce produit")
            
        serializer.save(product=product)

class ProductFormatImageListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        format_id = self.kwargs['format_id']
        return ProductImage.objects.filter(format_id=format_id)

    def perform_create(self, serializer):
        format_id = self.kwargs['format_id']
        product_format = get_object_or_404(ProductFormat, pk=format_id)
        
        if product_format.product.manufacturer != self.request.user:
            raise PermissionDenied("Vous n'êtes pas le fabricant de ce produit")
            
        serializer.save(format=product_format)


class DisputeListView(generics.ListCreateAPIView):
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'dispute_type']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['ADMIN', 'STAFF']:
            return Dispute.objects.all()
        return Dispute.objects.filter(Q(created_by=user) | Q(assigned_to=user))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class DisputeDetailView(generics.RetrieveUpdateAPIView):
    queryset = Dispute.objects.all()
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['ADMIN', 'STAFF']:
            return Dispute.objects.all()
        return Dispute.objects.filter(Q(created_by=user) | Q(assigned_to=user))

class DisputeMessageCreateView(generics.CreateAPIView):
    queryset = DisputeMessage.objects.all()
    serializer_class = DisputeMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        dispute_id = self.kwargs['dispute_id']
        dispute = get_object_or_404(Dispute, pk=dispute_id)
        
        if dispute.created_by != self.request.user and dispute.assigned_to != self.request.user:
            raise PermissionDenied("Vous n'êtes pas autorisé à contribuer à ce litige")
            
        serializer.save(dispute=dispute, sender=self.request.user)


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['report_type', 'created_at']

    def get_queryset(self):
        return Report.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        report = self.get_object()
        # Ici vous intégrerez la logique de génération du rapport
        # avec les librairies comme ReportLab (PDF) ou pandas (Excel)
        return Response({"status": "Report generation started"}, status=202)

class DashboardViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dashboard.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# views.py
class AdminStatsView(APIView):
    def get(self, request):
        data = {
            "total_users": User.objects.count(),
            "active_orders": Order.objects.filter(status="PROCESSING").count(),
            "monthly_sales": Order.objects.aggregate(total=Sum('total_amount'))
        }
        return Response(data)

# filters.py (django-filter)
class UserFilter(FilterSet):
    date_joined = DateFromToRangeFilter()
    class Meta:
        model = User
        fields = ['user_type', 'is_active']

# models.py
class Document(models.Model):
    file = models.FileField(upload_to='documents/%Y/%m/')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

# core/views.py
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.renderers import JSONRenderer

class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user_type', 'is_active', 'date_joined']
    renderer_classes = [JSONRenderer]  # Force le rendu JSON
    
    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


# core/views.py
class BulkProductUpdateView(APIView):
    permission_classes = [IsAdminUser]
    
    def patch(self, request):
        serializer = BulkProductUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            updates = []
            for item in serializer.validated_data:
                product = Product.objects.get(id=item['id'])
                for attr, value in item.items():
                    if attr != 'id':
                        setattr(product, attr, value)
                product.save()
                updates.append(product)
            return Response(ProductSerializer(updates, many=True).data)
        return Response(serializer.errors, status=400)

# core/views.py
import pandas as pd

class OrderExportView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        queryset = Order.objects.all().select_related('user')
        data = [{
            'ID': order.id,
            'Client': order.user.email,
            'Montant': order.total_amount,
            'Statut': order.get_status_display(),
            'Date': order.created_at
        } for order in queryset]
        
        format = request.query_params.get('format', 'csv')
        
        if format == 'excel':
            df = pd.DataFrame(data)
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename="commandes.xlsx"'
            df.to_excel(response, index=False)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="commandes.csv"'
            writer = csv.DictWriter(response, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
        return response

# core/views.py
class RetailPointMapView(generics.ListAPIView):
    serializer_class = RetailPointMapSerializer
    queryset = RetailPoint.objects.filter(is_active=True)
    
    def get_queryset(self):
        qs = super().get_queryset()
        if 'region' in self.request.query_params:
            qs = qs.filter(address__region=self.request.query_params['region'])
        return qs.select_related('address')


from django.db.models import Count, Sum
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAdminUser

class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = {
            "users": {
                "total": User.objects.count(),
                "by_type": dict(User.objects.values_list('user_type').annotate(count=Count('id')))
            },
            "orders": {
                "last_7_days": Order.objects.filter(
                    created_at__gte=timezone.now()-timedelta(days=7)
                    .aggregate(total=Sum('total_amount')))
            }
        }
        return Response(data)


import csv
from django.http import HttpResponse

class ExportOrdersView(APIView):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'User', 'Amount', 'Status'])
        
        for order in Order.objects.all().select_related('user'):
            writer.writerow([order.id, order.user.email, order.total_amount, order.status])
        
        return response