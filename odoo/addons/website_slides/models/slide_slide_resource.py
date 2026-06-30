# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.mimetypes import get_extension


class SlideResource(models.Model):
    _name = 'slide.slide.resource'
    _description = "Additional resource for a particular slide"

    slide_id = fields.Many2one('slide.slide', required=True, ondelete='cascade')
    resource_type = fields.Selection([('file', 'File'), ('url', 'Link')], required=True)
    name = fields.Char('Name', compute="_compute_name", readonly=False, store=True)
    data = fields.Binary('Resource', compute='_compute_reset_resources', store=True, readonly=False)
    file_name = fields.Char(store=True)
    link = fields.Char('Link', compute='_compute_reset_resources', store=True, readonly=False)
    download_url = fields.Char('Download URL', compute='_compute_download_url')

    _sql_constraints = [
        ('check_url', "CHECK (resource_type != 'url' OR link IS NOT NULL)", 'A resource of type url must contain a link.'),
        ('check_file_type', "CHECK (resource_type != 'file' OR link IS NULL)", 'A resource of type file cannot contain a link.'),
    ]

    @api.depends('resource_type')
    def _compute_reset_resources(self):
        for resource in self:
            if resource.resource_type == 'file':
                resource.link = False
                resource.data = resource.data
            else:
                resource.data = False
                resource.link = resource.link

    @api.depends('file_name', 'resource_type', 'data', 'link')
    def _compute_name(self):
        for resource in self:
            to_update = not resource.name or resource.name == _("Resource")
            if to_update:
                new_name = _("Resource")
                if resource.resource_type == 'file' and (resource.data or resource.file_name):
                    new_name = resource.file_name
                elif resource.resource_type == 'url':
                    new_name = resource.link
                resource.name = new_name

    @api.depends('name', 'file_name')
    def _compute_download_url(self):
        for resource in self:
            extension = get_extension(resource.file_name) if resource.file_name else ''
            if not resource.name:
                resource.download_url = False
                continue
            file_name = resource.name if resource.name.endswith(extension) else resource.name + extension
            resource.download_url = f'/web/content/slide.slide.resource/{resource.id}/data?' + url_encode({
                'download': 'true',
                'filename': file_name,
            })

    @api.constrains('data')
    def _check_link_type(self):
        for record in self:
            if record.resource_type != 'file' and record.data:
                raise ValidationError(_("Resource %(resource_name)s is a link and should not contain a data file", resource_name=record.name))
