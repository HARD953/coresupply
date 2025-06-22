from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Ajoutez des claims personnalisés
        token['user_type'] = user.user_type
        token['is_staff'] = user.is_staff
        return token

class AdminLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer