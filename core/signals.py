from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, Notification

@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    if not created and instance.status != instance._original_status:
        Notification.objects.create(
            user=instance.user,
            notification_type='ORDER_UPDATE',
            message=f"Votre commande #{instance.order_number} est maintenant {instance.get_status_display()}",
            related_object_id=instance.id
        )