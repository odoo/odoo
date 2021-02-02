# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models, tools


class UtmSource(models.Model):
    _name = 'utm.source'
    _description = 'UTM Source'

    name = fields.Char(string='Source Name', required=True)

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The name must be unique'),
    ]

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

        create_date = record.create_date or fields.date.today()
        create_date = fields.date.strftime(create_date, tools.DEFAULT_SERVER_DATE_FORMAT)
        model_description = self.env['ir.model']._get(record._name).name
        return _(
            '%(content)s (%(model_description)s created on %(create_date)s)',
            content=content, model_description=model_description, create_date=create_date,
        )


class UtmSourceMixin(models.AbstractModel):
    """Mixin responsible of generating the name of the source based on the content
    (field defined by _rec_name) of the record (mailing, social post,...).
    """
    _name = 'utm.source.mixin'
    _description = 'UTM Source Mixin'

    name = fields.Char('Name', related='source_id.name', readonly=False)
    source_id = fields.Many2one('utm.source', string='Source', required=True, ondelete='restrict', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        """Create the UTM sources if necessary, generate the name based on the content in batch."""
        # Create all required <utm.source>
        utm_sources = self.env['utm.source'].create([
            {'name': values.get('name') or self.env['utm.source']._generate_name(self, values.get(self._rec_name))}
            for values in vals_list
            if not values.get('source_id')
        ])

        # Update "vals_list" to add the ID of the newly created source
        vals_list_missing_source = [values for values in vals_list if not values.get('source_id')]
        for values, source in zip(vals_list_missing_source, utm_sources):
            values['source_id'] = source.id

        for values in vals_list:
            if 'name' in values:
                del values['name']

        return super().create(vals_list)

    def write(self, values):
        if values.get(self._rec_name) and not values.get('name'):
            values['name'] = self.env['utm.source']._generate_name(self, values[self._rec_name])
        if values.get('name'):
            values['name'] = self.env['utm.mixin']._get_unique_names(self._name, [values['name']])[0]

        super().write(values)

    def copy(self, default=None):
        """Increment the counter when duplicating the source."""
        default = default or {}
        default['name'] = self.env['utm.mixin']._get_unique_names(self._name, [self.name])[0]
        return super().copy(default)
