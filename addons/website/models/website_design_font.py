from odoo import api, models, fields
from odoo.exceptions import ValidationError


class WebsiteDesignFont(models.Model):
    _name = 'website.design.font'
    _description = 'Website Design Font'

    name = fields.Char(string='Name', required=True)
    is_local = fields.Boolean(string='Local', default=False)
    is_native = fields.Boolean(string='Native', default=True)
    attachment_id = fields.Many2one('ir.attachment', string='Attachment', ondelete='cascade')
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')

    @api.constrains('is_local', 'attachment_id')
    def _check_attachment(self):
        for record in self:
            if not record.is_local and record.attachment_id:
                raise ValidationError("Only local fonts can have an attachment.")

    def unlink(self):
        for record in self:
            if record.is_native:
                raise ValidationError("You cannot delete a native font.")
            if record.is_local:
                design = self.env['website.design'].search([('website_id', '=', record.website_id.id)])
                for field_name in design._fields:
                    field = design._fields[field_name]
                    if field.comodel_name == 'website.design.font' and design[field_name].id == record.id:
                        # Maybe set back to System Font
                        design[field_name] = False
                record.attachment_id = False
                record.attachment_id.unlink()

        return super().unlink()

    _sql_constraints = [
        ('name_local_website_unique', 'UNIQUE(name, is_local, website_id)', "This font already exists."),
    ]
