# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UtmSource(models.Model):
    _name = 'utm.source'
    _description = 'UTM Source'

    name = fields.Char(string='Source Name', required=True)

    _unique_name = models.Constraint(
        'UNIQUE(name)',
        'The name must be unique',
    )

    @api.model_create_multi
    def create(self, vals_list):
        new_names = self.env['utm.mixin']._get_unique_names(self._name, [vals.get('name') for vals in vals_list])
        for vals, new_name in zip(vals_list, new_names):
            vals['name'] = new_name
        return super().create(vals_list)

    def _generate_name(self, record, content):
        """Generate the UTM source name based on the content of the source."""
        if not content:
            return False

        content = content.replace('\n', ' ')
        if len(content) >= 24:
            content = f'{content[:20]}...'

        create_date = record.create_date or fields.Datetime.today()
        model_description = self.env['ir.model']._get(record._name).name
        return _(
            '%(content)s (%(model_description)s created on %(create_date)s)',
            content=content,
            model_description=model_description,
            create_date=fields.Date.to_string(create_date),
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_utm_source_record(self):
        utm_source_xml_ids = [
            key
            for key, (_label, model)
            in self.env['utm.mixin'].SELF_REQUIRED_UTM_REF.items()
            if model == 'utm.source'
        ]

        for xml_id in utm_source_xml_ids:
            utm_source = self.env.ref(xml_id, raise_if_not_found=False)
            if utm_source and utm_source in self:
                raise UserError(_(
                    "Oops, you can't delete the Source '%s'.\n"
                    "Doing so would be like tearing down a load-bearing wall \u2014 not the best idea.",
                    utm_source.name
                ))
