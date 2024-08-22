# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import api, fields, models


class Media(models.Model):
    _name = 'html_editor.media'
    _description = 'Media'
    _order = 'id desc'

    res_model = fields.Char('Resource Model', readonly=True, required=True)
    res_id = fields.Many2oneReference(
        'Resource ID',
        model_field='res_model',
        readonly=True,
        required=True
    )
    name = fields.Char('Name', required=True)
    media_content = fields.Binary('Media content', required=True)
    attachment_id = fields.Many2one('ir.attachment', 'Media attachment', compute='_compute_attachment_id', store=True, ondelete='cascade')
    url = fields.Char('Url', index='btree_not_null', size=1024)
    media_type = fields.Char('Media type', required=True)
    public = fields.Boolean('Is public document')

    @api.model_create_multi
    def create(self, vals):
        media_vals = []
        for val in vals:
            raw, datas = val.pop('raw', b''), val.pop('datas', None)
            media_vals.append({
                'name': val.get('name'),
                'media_content': datas or b64encode(raw),
                'public': val.get('public', val['res_model'] == 'ir.ui.view'),
                'res_model': val.pop('res_model'),
                'res_id': val.pop('res_id', 0),
                'url': val.pop('url', ''),
                'media_type': val.pop('media_type'),
            })
        media = super().create(media_vals)
        for i, medium in enumerate(media):
            attach_dict = vals[i]
            # The automatic creation of an attachment through the binary field
            # doesn't happen with url-only media. We do it explicitly.
            if not medium.media_content:
                attach_dict.update({
                    'res_id': medium.id,
                    'res_model': 'html_editor.media',
                    'res_field': 'media_content',  # fake link to ease searches.
                    'type': 'url',
                    'url': medium.url,
                })
                self.env['ir.attachment'].create(attach_dict)
            else:
                # By default, a binary field creates an attachment over whose
                # fields we have little to no control at creation. We write (and
                # might override) the ones that were explicitly given.
                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', 'html_editor.media'),
                    ('res_field', '=', 'media_content'),
                    ('res_id', '=', medium.id),
                ], limit=1)
                attach_dict['mimetype'] = attach_dict.get('mimetype') or attachment.mimetype
                # Binary attachment with a URL (e.g. Unsplash)
                if medium.url and not attachment.url:
                    attach_dict['url'] = medium.url
                attachment.update(attach_dict)
        return media

    @api.depends('media_content', 'url')
    def _compute_attachment_id(self):
        for medium in self:
            medium.attachment_id = self.env['ir.attachment'].search([
                ('res_model', '=', 'html_editor.media'),
                ('res_field', '=', 'media_content'),
                ('res_id', '=', medium.id),
            ], limit=1)

    def _get_media_info(self):
        """Returns a dict with the values that we need on the media dialog."""
        media_fields = [
            'name',
            'res_model',
            'res_id',
            'url',
            'public',
        ]
        attachment_fields = [
            'description',
            'mimetype',
            'original_id',
            'type',
            'checksum',
            'access_token',
            'image_src',
            'image_width',
            'image_height',
        ]
        media_info = self.web_read(
            {field: {} for field in media_fields}
            | {
                'attachment_id': {
                    'fields': {
                        field: {} for field in attachment_fields
                    }
                }
            }
        )[0]
        attachment_id = media_info['attachment_id'].pop('id')
        return media_info | media_info['attachment_id'] | {'attachment_id': attachment_id}
