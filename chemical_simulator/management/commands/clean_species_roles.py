# chemical_simulator/management/commands/clean_species_roles.py

from django.core.management.base import BaseCommand
from chemical_simulator.models import Species

class Command(BaseCommand):
    help = 'Limpa e normaliza os papéis das espécies químicas'

    def handle(self, *args, **options):
        ROLE_MAP = {
            'Reagente': 'reactant',
            'Produto': 'product',
            'Catalisador': 'catalyst',
            'Solvente': 'solvent',
            'Intermediário': 'intermediate',
        }

        self.stdout.write("🔍 Verificando espécies...")
        updated = 0
        skipped = 0
        errors = 0

        for species in Species.objects.all():
            current_role = species.simulation_role
            
            # Se o papel já está em formato correto, pular
            if current_role in ROLE_MAP.values():
                skipped += 1
                continue
            
            # Tentar mapear
            new_role = ROLE_MAP.get(current_role)
            
            if new_role:
                species.simulation_role = new_role
                species.save()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Atualizado: {species.name} - {current_role} → {new_role}")
                )
                updated += 1
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Erro: {species.name} - papel inválido '{current_role}'")
                )
                errors += 1

        self.stdout.write("\n📊 Resultado:")
        self.stdout.write(f"   Atualizadas: {updated}")
        self.stdout.write(f"   Já corretas: {skipped}")
        self.stdout.write(f"   Erros: {errors}")