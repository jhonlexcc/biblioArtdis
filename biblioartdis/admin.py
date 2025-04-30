from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields, widgets
from import_export.formats import base_formats
from reversion.admin import VersionAdmin
from .models import Usuario, Autor, Libro, Sugerencia, Coleccion, Revista, VisitaLibro, Imagen, Categoria
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
import reversion
from import_export.widgets import IntegerWidget
from django.utils import timezone
import datetime

# Registrar el modelo Libro con reversion
reversion.register(Libro)

class CustomImportExportModelAdmin(ImportExportModelAdmin):
    def get_import_formats(self):
        """Returns available import formats."""
        formats = [base_formats.CSV, base_formats.XLSX]
        return [f for f in formats if f().can_import()]
        
    def get_import_resource_class(self):
        """Returns the import resource class to use for this ModelAdmin."""
        return self.resource_class

# Resource classes para cada modelo
class UsuarioResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = Usuario
        skip_unchanged = True
        exclude = ['usuario_id', 'user']
        import_id_fields = []  # Don't require any specific ID fields
        
    def set_encoding(self, encoding):
        self._encoding = encoding
    
    def before_import_row(self, row, **kwargs):
        # Set up silent debugging (no terminal output)
        import json
        debug_mode = False  # Set to False to disable all debug output
        
        # Handle special case where all data is in a single column
        for key in list(row.keys()):
            if ',' in key and len(row.keys()) < 3:  # Likely a merged header
                # This is probably a merged header like 'nombres,apepat,apemat,...'
                header_parts = key.split(',')
                values = str(row[key]).split(',')
                
                # Create individual columns from the split data
                if len(values) >= len(header_parts):
                    for i, header in enumerate(header_parts):
                        if i < len(values):
                            header_clean = header.strip()
                            row[header_clean] = values[i].strip()
                
                # Keep the original column to avoid losing data
                # but rename it to avoid confusion
                if key in row:
                    row['original_data'] = row[key]
        
        # Auto-map common variations of column names
        field_mapping = {
            # Common variations for field names
            'nombre': 'nombres',
            'name': 'nombres',
            'cedula': 'ci',
            'cedula de identidad': 'ci',
            'cédula': 'ci',
            'cédula de identidad': 'ci',
            'id': 'ci',
            'identificacion': 'ci',
            'identificación': 'ci',
            'email': 'correo',
            'mail': 'correo',
            'e-mail': 'correo',
            'apellido paterno': 'apepat',
            'apellidop': 'apepat',
            'apellido materno': 'apemat',
            'apellidom': 'apemat',
            'tipo': 'tipo_usuario',
            'usuario': 'tipo_usuario',
            'telefono': 'nro_celular',
            'teléfono': 'nro_celular',
            'celular': 'nro_celular',
            'movil': 'nro_celular',
            'móvil': 'nro_celular',
        }
        
        # Apply field mapping (case insensitive)
        original_keys = list(row.keys())
        for key in original_keys:
            if key not in ['original_data']:  # Skip our special fields
                # Check if this key should be mapped to a different field name
                key_lower = key.lower().strip()
                if key_lower in field_mapping and key_lower != key:
                    # Map the field if it exists in our mapping and the target field doesn't already exist
                    target_field = field_mapping[key_lower]
                    if target_field not in row or not row[target_field]:
                        row[target_field] = row[key]
        
        # Set default values for date fields if not provided
        from django.utils import timezone
        import datetime
        
        # Set fecha_alta to current date/time if not provided
        if not row.get('fecha_alta'):
            row['fecha_alta'] = timezone.now()
            
        # Set fecha_baja to one year from now if not provided
        if not row.get('fecha_baja'):
            one_year = timezone.now() + datetime.timedelta(days=365)
            row['fecha_baja'] = one_year
            
        # Set esta_activo to True if not provided or ensure boolean value
        if 'esta_activo' not in row or row['esta_activo'] == '':
            row['esta_activo'] = True
        elif isinstance(row['esta_activo'], str):
            # Convert string '1' or 'True' to boolean True
            row['esta_activo'] = row['esta_activo'].lower() in ['1', 'true', 'yes', 'y', 'si', 's']
        
        # Only use Importado_ prefix as a last resort when required fields are still missing
        for field in ['nombres', 'ci', 'correo', 'extension', 'tipo_usuario']:
            if not row.get(field):
                row[field] = f'Importado_{field}'
                
        return row
    
    def after_import_instance(self, instance, new, **kwargs):
        # Additional processing after instance is imported
        # Set user to a default user if none provided
        if not instance.user:
            try:
                from django.contrib.auth.models import User
                # Try to get the first admin user
                admin_user = User.objects.filter(is_staff=True).first()
                if admin_user:
                    instance.user = admin_user
            except Exception:
                pass
        return instance

class LibroResource(resources.ModelResource):
    autores_list = fields.Field()
    categorias_list = fields.Field()
    _encoding = 'utf-8'

    class Meta:
        model = Libro
        fields = ('id_libro', 'tipo', 'titulo', 'edicion', 'categoria', 
                 'img_portada', 'archivo_autorizacion', 'autores_list',
                 'fecha_publicacion', 'descripcion', 'palabra_clave', 
                 'descarga_autorizada', 'pdf_url', 'categorias_list')
        export_order = fields

    def set_encoding(self, encoding):
        """Set the encoding to use for this import"""
        self._encoding = encoding

    def dehydrate_autores_list(self, libro):
        return ', '.join([autor.nombre for autor in libro.autores.all()])

    def dehydrate_categorias_list(self, libro):
        return ', '.join([cat.nom_cat for cat in libro.categorias.all()])

class AutorResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = Autor
        
    def set_encoding(self, encoding):
        self._encoding = encoding

class SugerenciaResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = Sugerencia
        
    def set_encoding(self, encoding):
        self._encoding = encoding

class ColeccionResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = Coleccion
        
    def set_encoding(self, encoding):
        self._encoding = encoding

class RevistaResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = Revista
        
    def set_encoding(self, encoding):
        self._encoding = encoding

class VisitaLibroResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = VisitaLibro
        
    def set_encoding(self, encoding):
        self._encoding = encoding

class ImagenResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = Imagen
        
    def set_encoding(self, encoding):
        self._encoding = encoding

class CategoriaResource(resources.ModelResource):
    _encoding = 'utf-8'
    
    class Meta:
        model = Categoria
        
    def set_encoding(self, encoding):
        self._encoding = encoding

@admin.register(Usuario)
class UsuarioAdmin(ImportExportModelAdmin, VersionAdmin):
    resource_class = UsuarioResource
    list_display = ('nombres', 'apepat', 'apemat', 'ci', 'correo', 'tipo_usuario', 'nro_celular')
    list_filter = ('tipo_usuario', 'extension', 'esta_activo')
    search_fields = ('nombres', 'apepat', 'apemat', 'ci', 'correo')
    ordering = ('-fecha_alta',)
    readonly_fields = ('fecha_alta',)
    formats = [base_formats.CSV, base_formats.XLSX]
    
    def get_import_formats(self):
        """Returns available import formats."""
        return [f for f in self.formats if f().can_import()]

@admin.register(Libro)
class LibroAdmin(ImportExportModelAdmin, VersionAdmin):
    resource_class = LibroResource
    list_display = ('id_libro', 'titulo', 'tipo', 'categoria', 'descarga_autorizada', 'get_autores')
    search_fields = ('titulo', 'palabra_clave', 'autores__nombre')
    list_filter = ('tipo', 'categoria', 'descarga_autorizada', 'fecha_publicacion')
    filter_horizontal = ('autores', 'categorias')
    date_hierarchy = 'fecha_publicacion'
    list_per_page = 20
    history_latest_first = True
    history_list_display = ['titulo', 'tipo', 'categoria']
    ignore_duplicate_revisions = True
    recover_list_display = ['titulo', 'tipo', 'categoria']
    
    def get_autores(self, obj):
        return ", ".join([autor.nombre for autor in obj.autores.all()])
    get_autores.short_description = 'Autores'

    # Acciones personalizadas
    actions = ['marcar_como_autorizado', 'marcar_como_no_autorizado', 'generar_reporte']
    
    def marcar_como_autorizado(self, request, queryset):
        updated = queryset.update(descarga_autorizada=True)
        self.message_user(request, f'{updated} libros marcados como autorizados.')
    marcar_como_autorizado.short_description = "Marcar libros seleccionados como autorizados"

    def marcar_como_no_autorizado(self, request, queryset):
        updated = queryset.update(descarga_autorizada=False)
        self.message_user(request, f'{updated} libros marcados como no autorizados.')
    marcar_como_no_autorizado.short_description = "Marcar libros seleccionados como no autorizados"

    # Vista previa de PDF y portada
    readonly_fields = ('preview_portada', 'preview_pdf')

    def preview_portada(self, obj):
        if obj.img_portada:
            return mark_safe(f'<img src="{obj.img_portada.url}" width="150"/>')
        return "Sin portada"
    preview_portada.short_description = 'Vista previa de portada'

    def preview_pdf(self, obj):
        if obj.pdf_url:
            return mark_safe(f'<a href="{obj.pdf_url}" target="_blank">Ver PDF</a>')
        return "Sin PDF"
    preview_pdf.short_description = 'Vista previa de PDF'

    # Ayuda contextual
    help_text = {
        'titulo': 'Ingrese el título completo del libro',
        'palabra_clave': 'Separe las palabras clave con comas',
        'descripcion': 'Breve resumen del contenido del libro'
    }

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name, text in self.help_text.items():
            if field_name in form.base_fields:
                form.base_fields[field_name].help_text = text
        return form

    # Personalización de mensajes de cambio
    def save_model(self, request, obj, form, change):
        with reversion.create_revision():
            super().save_model(request, obj, form, change)
            reversion.set_user(request.user)
            reversion.set_comment("Cambio realizado desde el admin")
        if change:
            messages.info(request, f'El libro "{obj.titulo}" ha sido actualizado exitosamente.')
        else:
            messages.success(request, f'El libro "{obj.titulo}" ha sido creado exitosamente.')

@admin.register(Autor)
class AutorAdmin(ImportExportModelAdmin):
    resource_class = AutorResource
    list_display = ('id_autor', 'nombre')
    search_fields = ('nombre',)

@admin.register(Sugerencia)
class SugerenciaAdmin(ImportExportModelAdmin):
    resource_class = SugerenciaResource
    list_display = ('id_sugerencia', 'titulo_sugerencia', 'autor_sugerencia', 'estado_respuesta')
    list_filter = ('estado_respuesta',)

@admin.register(Revista)
class RevistaAdmin(ImportExportModelAdmin):
    resource_class = RevistaResource
    list_display = ('id_revista', 'nro_revista', 'coleccion')
    search_fields = ('nro_revista',)
    list_filter = ('coleccion',)

@admin.register(Coleccion)
class ColeccionAdmin(ImportExportModelAdmin):
    resource_class = ColeccionResource
    list_display = ('id_coleccion', 'nomb_colecc', 'orden')
    search_fields = ('nomb_colecc',)
    list_editable = ('orden',)

@admin.register(VisitaLibro)
class VisitaLibroAdmin(ImportExportModelAdmin):
    resource_class = VisitaLibroResource
    list_display = ('visitante', 'libro_visitado', 'fecha_visualizacion')
    list_filter = ('fecha_visualizacion', 'libro_visitado')
    date_hierarchy = 'fecha_visualizacion'
    readonly_fields = ('fecha_visualizacion',)
    search_fields = ('visitante__nombres', 'libro_visitado__titulo')
    list_per_page = 50

@admin.register(Imagen)
class ImagenAdmin(ImportExportModelAdmin):
    resource_class = ImagenResource
    list_display = ('id_Imagen', 'titulo', 'autorImg', 'fecha_subida')
    search_fields = ('titulo', 'autorImg')

@admin.register(Categoria)
class CategoriaAdmin(ImportExportModelAdmin):
    resource_class = CategoriaResource
    list_display = ('id_categoria', 'nom_cat')
    search_fields = ('nom_cat',)
