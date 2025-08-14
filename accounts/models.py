# Modelo User (extensão de AbstractUser com campo role)

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class RoleChoices(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        PROFESSOR = 'professor', 'Professor'
        ALUNO = 'aluno', 'Aluno'
    
    role = models.CharField(
        max_length=10,
        choices=RoleChoices.choices,
        default=RoleChoices.ALUNO,
        verbose_name='Perfil'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Utilizador'
        verbose_name_plural = 'Utilizadores'
    
    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'