# mi_website_ext/models/website_gallery.py
from odoo import models, fields

class WebsiteGalleryAlbum(models.Model):
    _name = 'website.gallery.album'
    _description = 'Álbum de Galería del Sitio Web'
    _inherit = ['image.mixin'] # Para tener una imagen de portada
    _order = 'sequence, create_date desc'

    name = fields.Char(string="Título del Álbum", required=True, translate=True)
    description = fields.Text(string="Descripción", translate=True)
    is_published = fields.Boolean(string="Publicado", default=True, index=True)
    sequence = fields.Integer(string="Secuencia", default=10)

    # Relación para saber qué fotos pertenecen a este álbum
    photo_ids = fields.One2many('website.gallery.photo', 'album_id', string="Fotos")

    # La imagen principal del álbum (image_1920) servirá como portada

class WebsiteGalleryPhoto(models.Model):
    _name = 'website.gallery.photo'
    _description = 'Foto de Galería del Sitio Web'
    _inherit = ['image.mixin'] # Cada foto tendrá su propio campo de imagen
    _order = 'sequence, create_date desc'

    name = fields.Char(string="Título/Descripción de la Foto", translate=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    album_id = fields.Many2one('website.gallery.album', string="Álbum", required=True, ondelete='cascade')

    # La imagen de la foto se guardará en el campo image_1920 heredado de image.mixin