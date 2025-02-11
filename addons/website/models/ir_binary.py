from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record(
            self, xmlid=None, res_model='ir.attachment', res_id=None,
            access_token=None,
    ):
        record = None
        if xmlid:
            website = self.env['website'].get_current_website()
            if website.theme_id:
                domain = [('key', '=', xmlid), ('website_id', '=', website.id)]
                Attachment = self.env['ir.attachment']
                if self.env.user.share:
                    domain.append(('public', '=', True))
                    Attachment = Attachment.sudo()
                record = Attachment.search(domain, limit=1)

        if not record:
            record = super()._find_record(xmlid, res_model, res_id, access_token)

        return record

    def _find_record_check_access(self, record, access_token):
        if 'website_published' in record._fields and record.sudo().website_published:
            return record

        return super()._find_record_check_access(record, access_token)

    def _record_to_stream(self, record, field_name):
        if (
            'website_published' in record._fields
            and field_name in record._fields
            and not record._fields[field_name].groups
            and record.sudo().website_published
        ):
            record = record.sudo()
        return super()._record_to_stream(record, field_name)
