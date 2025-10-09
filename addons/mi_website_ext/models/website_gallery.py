# mi_website_ext/models/website_gallery.py
from odoo import models, fields

class WebsiteGalleryAlbum(models.Model):
    _name = 'website.gallery.album'
    _description = 'Álbum de Galería del Sitio Web'
    _inherit = ['image.mixin'] 
    _order = 'sequence, create_date desc'

    name = fields.Char(string="Título del Álbum", required=True, translate=True)
    description = fields.Text(string="Descripción", translate=True)
    is_published = fields.Boolean(string="Publicado", default=True, index=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    photo_ids = fields.One2many('website.gallery.photo', 'album_id', string="Fotos")

class WebsiteGalleryPhoto(models.Model):
    _name = 'website.gallery.photo'
    _description = 'Foto de Galería del Sitio Web'
    _inherit = ['image.mixin'] 
    _order = 'sequence, create_date desc'

    name = fields.Char(string="Título/Descripción de la Foto", translate=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    album_id = fields.Many2one('website.gallery.album', string="Álbum", required=True, ondelete='cascade')

    is_video = fields.Boolean(string="¿Es un video?", default=False)
    video_file = fields.Binary(string="Archivo de Video")
    video_filename = fields.Char(string="Nombre del Video")
