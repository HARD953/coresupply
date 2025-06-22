from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
# OU si vous avez créé auth.py :
from .auth import AdminLoginView
from .views import AdminUserListView,OrderExportView, BulkProductUpdateView,RetailPointMapView  # ✅ Import the view

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet, basename='report')
router.register(r'dashboards', views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    # --- Authentification/Utilisateurs ---
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/me/', views.UserDetailView.as_view(), name='user-detail'),
    
    # --- Adresses ---
    path('addresses/', views.AddressListView.as_view(), name='address-list'),
    
    # --- Points de vente ---
    path('retail-points/', views.RetailPointCreateView.as_view(), name='retail-point-list'),
    
    # --- Produits ---
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:product_id>/formats/', views.ProductFormatCreateView.as_view(), name='product-format-create'),
    
    # --- Inventaire ---
    path('inventory/', views.InventoryListView.as_view(), name='inventory-list'),
    path('inventory/<int:pk>/', views.InventoryDetailView.as_view(), name='inventory-detail'),
    path('retail-points/<int:retail_point_id>/inventory/', views.RetailPointInventoryView.as_view(), name='retail-point-inventory'),
    path('stock-movements/', views.StockMovementCreateView.as_view(), name='stock-movement-create'),
    
    # --- Panier & Commandes ---
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/items/', views.CartItemView.as_view(), name='cart-items'),
    path('cart/items/<int:pk>/', views.CartItemView.as_view(), name='cart-item-detail'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    
    # --- Catégories ---
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
     # --- Notice ---
    path('token-transactions/', views.TokenTransactionView.as_view(), name='token-transactions'),
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/mark-as-read/', views.MarkNotificationAsReadView.as_view(), name='mark-notification-read'),

     # Formats de produits
    path('product-formats/', views.ProductFormatListView.as_view(), name='product-format-list'),
    path('product-formats/<int:pk>/', views.ProductFormatDetailView.as_view(), name='product-format-detail'),
    path('products/<int:product_id>/formats/', views.ProductFormatListCreateView.as_view(), name='product-format-list-create'),

    # Images produits
    path('product-images/', views.ProductImageListView.as_view(), name='product-image-list'),
    path('product-images/<int:pk>/', views.ProductImageDetailView.as_view(), name='product-image-detail'),
    path('products/<int:product_id>/images/', views.ProductImageListCreateView.as_view(), name='product-image-list-create'),
    path('product-formats/<int:format_id>/images/', views.ProductFormatImageListCreateView.as_view(), name='product-format-image-list-create'),

    path('disputes/', views.DisputeListView.as_view(), name='dispute-list'),
    path('disputes/<int:pk>/', views.DisputeDetailView.as_view(), name='dispute-detail'),
    path('disputes/<int:dispute_id>/messages/', views.DisputeMessageCreateView.as_view(), name='dispute-message-create'),

     # Auth
    path('auths/login/', AdminLoginView.as_view(), name='admin-login'),
    
    # Admin
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/orders/export/', OrderExportView.as_view(), name='order-export'),
    
    # Products
    path('products/bulk/', BulkProductUpdateView.as_view(), name='bulk-product-update'),
    
    # Retail Points
    path('retail-points/map/', RetailPointMapView.as_view(), name='retail-point-map'),
]

urlpatterns += router.urls