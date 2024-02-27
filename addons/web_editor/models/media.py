# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import api, fields, models
from odoo.tools.sql import SQL


class Media(models.Model):
    _name = 'web_editor.media'
    _description = 'Media'
    _order = 'id desc'

    res_model = fields.Char('Resource Model', readonly=True, required=True)
    res_id = fields.Many2oneReference(
        'Resource ID',
        model_field='res_model',
        readonly=True,
        required=True
    )
    media_content = fields.Binary('Media content', required=True)
    url = fields.Char('Url', index='btree_not_null', size=1024)
    public = fields.Boolean('Is public document')
    hidden = fields.Boolean('Is hidden from media dialog', default=False)

    @api.model_create_multi
    def create(self, vals):
        media_vals = []
        for val in vals:
            raw, datas = val.pop('raw', b''), val.pop('datas', None)
            media_vals.append({
                'public': val.get('public', val['res_model'] == 'ir.ui.view'),
                'res_model': val.pop('res_model'),
                'res_id': val.pop('res_id', 0),
                'media_content': datas or b64encode(raw),
                'url': val.pop('url', ''),
            })
        media = super().create(media_vals)
        for i, medium in enumerate(media):
            attach_dict = vals[i]
            # The automatic creation of an attachment through the binary field
            # doesn't happen with url-only media. We do it explicitly.
            if not medium.media_content:
                attach_dict.update({
                    'res_id': medium.id,
                    'res_model': 'web_editor.media',
                    'type': 'url',
                    'url': medium.url,
                })
                self.env['ir.attachment'].create(attach_dict)
            else:
                # By default, a binary field creates an attachment over whose
                # fields we have little to no control at creation. We write (and
                # might override) the ones that were explicitly given.
                attachment = medium._get_attachment()
                attach_dict['mimetype'] = attach_dict.get('mimetype') or attachment.mimetype
                # Binary attachment with a URL (e.g. Unsplash)
                if medium.url and not attachment.url:
                    attach_dict['url'] = medium.url
                attachment.update(attach_dict)
        return media

    def _get_attachment(self):
        """Gets the attachment linked to the media."""
        self.ensure_one()
        res_field = 'media_content' if self.media_content else None
        return self.env['ir.attachment'].search([
            ('res_field', '=', res_field),
            ('res_id', '=', self.id),
            ('res_model', '=', 'web_editor.media'),
        ])

    def _fetch_media_attachments(self, media_domain, attachments_domain, offset, limit, **kwargs):
        """
        Fetches the `ir_attachment`s linked to some `web_editor.media`.

        :param media_domain: Search domain for the `web_editor.media` model.
        :param attachments_domain: Search domain for the `ir_attachment` model.
        :param int offset: Number of records to skip.
        :param int limit: Maximum number of records to return.
        :rtype: list(dict)
        """
        IrAttachment = self.env['ir.attachment']
        fields = self._get_media_dialog_fields()
        select_fields = (
            [SQL.identifier(IrAttachment._table, field) for field in fields['attachment_fields']]
            + [SQL.identifier(self._table, field) for field in fields['media_fields']]
        )
        media_where_clause = self._where_calc(media_domain).where_clause
        attachments_where_clause = IrAttachment._where_calc(attachments_domain).where_clause

        query = SQL("""
            SELECT %(select_fields)s
              FROM %(web_editor_media)s
              JOIN "ir_attachment"
                ON (
                    "ir_attachment"."res_id"=%(web_editor_media)s.id
                    AND "ir_attachment"."res_model"='web_editor.media'
                )
             WHERE %(media_where_clause)s
                   AND %(attachments_where_clause)s
          ORDER BY "ir_attachment"."id" DESC
            OFFSET %(offset)s
             LIMIT %(limit)s;
        """,
            select_fields=SQL(', ').join(select_fields),
            web_editor_media=SQL.identifier(self._table),
            media_where_clause=media_where_clause,
            attachments_where_clause=attachments_where_clause,
            offset=offset,
            limit=limit,
        )

        self._cr.execute(query.code, query.params)
        attachments = []
        all_fields = fields['attachment_fields'] + fields['media_fields']
        for result in self._cr.fetchall():
            attachment = {all_fields[i]: result[i] for i in range(len(all_fields))}
            # We can't directly query those fields in SQL, as they are computed.
            # To avoid useless queries, we only fetch them if we have an image.
            if attachment['mimetype'].split('/')[0] == 'image':
                image_info = IrAttachment.search_read(
                    [('id', '=', attachment['id'])],
                    ['image_src', 'image_width', 'image_height'],
                )[0]
                attachment.update(image_info)
            attachments.append(attachment)

        return attachments

    def _get_media_info(self):
        """Returns a dict with the values that we need on the media dialog."""
        attachment = self._get_attachment()
        fields = self._get_media_dialog_fields(True)
        attachment_info = attachment._read_format(fields['attachment_fields'])[0]
        media_info = self._read_format(fields['media_fields'])[0]
        media_info.pop('id')  # We keep the id of the ir.attachment
        media = dict(attachment_info)
        media.update(media_info)

        return media

    def _get_media_dialog_fields(self, with_computed=False):
        """Returns the fields needed for the media dialog.

        :param with_computed: Whether to also fetch computed fields.
        :return: dict of 2 lists (`attachment_fields`, `media_fields`) of fields
        (str)
        """
        attachment_fields = [
            'id',
            'name',
            'description',
            'mimetype',
            'checksum',
            'url',
            'type',
            'public',
            'access_token',
            'original_id',
        ]
        media_fields = [
            'res_id',
            'res_model',
        ]
        if with_computed:
            attachment_fields.extend(['image_src', 'image_width', 'image_height'])
        return {'attachment_fields': attachment_fields, 'media_fields': media_fields}
