# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from sqlite3 import ProgrammingError

from dateutil.relativedelta import relativedelta
from itertools import repeat

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import groupby
from odoo.tools.float_utils import float_round


ODOO_ICONS_CDN_URL = 'https://download.odoocdn.com/icons'
KPI_FIELDS = ['value_last_24_hours', 'value_last_7_days', 'value_last_30_days']


class DigestKpi(models.Model):
    _name = 'digest.kpi'
    _description = 'Kpi'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(required=True, default=0)
    res_model_id = fields.Many2one('ir.model', 'Model', ondelete='cascade', required=True)
    company_field = fields.Many2one(
        'ir.model.fields', 'Company Field',
        domain="[('model_id', '=', res_model_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.company')]",
        compute="_compute_company_field", store=True, readonly=False, precompute=True,
        required=False,
        help="Specify the field used for grouping by company.")

    # Standard computation
    agg_mode = fields.Selection(
        [('count', 'Count'), ('sum', 'Sum'), ('avg', 'Average'), ('neg_sum', 'Negative Sum'), ('neg_avg', 'Negative Average'), ('custom', 'Custom')],
        default='count', string='Aggregation Mode', required=True)
    agg_field = fields.Many2one(
        'ir.model.fields', 'Aggregation Field',
        domain="[('model_id', '=', res_model_id), ('ttype', 'in', ['float', 'integer', 'monetary']), ('name', '!=', 'id')]",
        compute="_compute_agg_field", store=True, readonly=False,
        required=False,
        help="Specify the field used for aggregating value (for summing, averaging, ...).")
    date_field = fields.Many2one(
        'ir.model.fields', 'Date Field',
        domain="[('model_id', '=', res_model_id), ('ttype', '=', ['datetime', 'date'])]",
        compute="_compute_date_field", store=True, readonly=False, precompute=True,
        required=False,
        help="Specify the field used for determining periods (Last 7 days, ...).")
    domain = fields.Char('Domain', required=False)

    # Custom computation
    agg_custom = fields.Many2one('ir.actions.server', required=False, ondelete='cascade')
    agg_custom_code = fields.Text(
        "Custom Code", compute="_compute_agg_custom_code", store=True, readonly=False
    )

    # Action
    module_id = fields.Many2one(
        'ir.module.module', 'Module', ondelete='set null',
        domain="['|', ('name', '=', 'base'), '&', ('state', '=', 'installed'), ('application', '=', True)]")
    action_menu_root_available = fields.Many2many('ir.ui.menu', compute="_compute_action_menu_root_available")
    action_menu_root_id = fields.Many2one('ir.ui.menu', string="Module Menu Root",
                                          domain="[('id', 'in', action_menu_root_available)]")
    actions_available = fields.Many2many('ir.actions.act_window', compute='_compute_actions_available')
    action_id = fields.Many2one('ir.actions.actions', string="Action", ondelete="set null",
                                domain="[('id', 'in', actions_available)]")
    action_url = fields.Char('Action URL', compute='_compute_action_url')
    icon_url = fields.Char('Icon URL', compute='_compute_icon_url', compute_sudo=True)

    # Security
    group_ids = fields.Many2many(
        'res.groups', string='Allowed Groups',
        default=lambda self: self.env.ref('base.group_user'),
        help="To read this kpi, user needs to be at least in one of these groups.")

    @api.depends('agg_mode', 'res_model_id')
    def _compute_company_field(self):
        self._default_field('company_field', self._allowed_company_fields_by_model(), 'company_id')

    @api.depends('agg_mode', 'res_model_id')
    def _compute_agg_field(self):
        self._default_field('agg_field', self._allowed_agg_fields_by_model())

    @api.depends('agg_mode', 'res_model_id')
    def _compute_date_field(self):
        self._default_field('date_field', self._allowed_date_fields_by_model(), 'create_date')

    def _default_field(self, field_name, allowed_fields_by_model, default_field=None):
        for kpi in self:
            if kpi.agg_mode == 'custom':
                self[field_name] = False
            if not kpi.res_model_id:
                continue
            field_value = self[field_name]
            allowed_fields = allowed_fields_by_model.get(kpi.res_model_id.id, {})
            if field_value in allowed_fields:
                continue
            self[field_name] = next(
                (field_id for field_id, field_name in allowed_fields.items() if field_name == default_field), False)

    @api.depends('action_id')
    def _compute_action_menu_root_available(self):
        # TODO: use self.env['ir.ui.menu'].load_menus(False)
        for kpi in self:
            menus = self.env['ir.ui.menu'].search([('action', 'like', f'%,{kpi.action_id.id}')])
            kpi.action_menu_root_available = self.env['ir.ui.menu'].browse(
                list({int(m.parent_path.split('/')[0]) for m in menus}))

    @api.depends('module_id')
    def _compute_actions_available(self):
        # TODO: batch it if possible
        for kpi in self:
            kpi.actions_available = [a.id for a in self.env['ir.ui.menu'].search([
                ('action', '!=', False),
                ('id', 'in', self.env['ir.model.data']._search([
                    ('module', '=', kpi.module_id.name),
                    ('model', '=', 'ir.ui.menu')]).select('res_id'))]).mapped('action')]

    @api.depends('module_id', 'action_id')
    def _compute_action_url(self):
        self.action_url = False
        for kpi in self:
            if kpi.action_id:
                kpi.action_url = f'/odoo/action-{kpi.action_id.id}' + (
                    f'?menu_id={kpi.action_menu_root_id.id}' if kpi.action_menu_root_id else '')

    @api.depends('agg_custom.code', 'agg_mode')
    def _compute_agg_custom_code(self):
        for kpi in self:
            if kpi.agg_custom:
                kpi.agg_custom_code = kpi.agg_custom.code
            elif kpi.agg_mode == 'custom' and not kpi.agg_custom:
                kpi.agg_custom_code = """# The action must return a numeric value for each company of env.context.get('companies')
# for the interval [env.context.get('start'), env.context.get('end')[
# Allowed formats are integer, float or monetary. In case of monetary, the returned values must be expressed in the company monetary.
action = ({company.id: 0 for company in env.context.get('companies')}, 'integer')"""

    @api.depends('module_id')
    def _compute_icon_url(self):
        for kpi in self:
            if not kpi.module_id:
                kpi.icon_url = False
            elif kpi.module_id.name == 'base':
                kpi.icon_url = f'{ODOO_ICONS_CDN_URL}/base/static/description/settings.png'
            else:
                kpi.icon_url = f'{ODOO_ICONS_CDN_URL}/{kpi.module_id.name}/static/description/icon.png'

    @api.constrains('agg_mode', 'res_model_id', 'date_field')
    def _check_date_field(self):
        self._check_field('date_field', self._allowed_date_fields_by_model())

    @api.constrains('agg_mode', 'res_model_id', 'company_field')
    def _check_company_field(self):
        self._check_field('company_field', self._allowed_company_fields_by_model(),
                          ignore_agg_modes=['count', 'custom'], required=False)

    @api.constrains('agg_mode', 'res_model_id', 'agg_field')
    def _check_agg_field(self):
        self._check_field('agg_field', self._allowed_agg_fields_by_model(), ignore_agg_modes=['count', 'custom'])

    def _allowed_date_fields_by_model(self):
        return self._allowed_fields_by_model(
            [('model_id', 'in', self.res_model_id.ids), ('ttype', '=', ['datetime', 'date'])])

    def _allowed_agg_fields_by_model(self):
        return self._allowed_fields_by_model(
            [('model_id', '=', self.res_model_id.ids),
             ('ttype', 'in', ['float', 'integer', 'monetary']), ('name', '!=', 'id')])

    def _allowed_company_fields_by_model(self):
        return self._allowed_fields_by_model(
            [('model_id', '=', self.res_model_id.ids), ('ttype', '=', 'many2one'), ('relation', '=', 'res.company')])

    def _allowed_fields_by_model(self, domain):
        return {
            model[0]: {r['id']: r['name'] for r in records}
            for model, records in groupby(
                self.env['ir.model.fields'].search_read(domain, ['model_id', 'name']), lambda r: r['model_id'])
        }

    @api.model
    def _check_field(self, field_name, allowed_fields_by_model, required=True, ignore_agg_modes=None):
        for kpi in self:
            if (not ignore_agg_modes and kpi.agg_mode == 'custom') or (
                    ignore_agg_modes and kpi.agg_mode in ignore_agg_modes):
                continue
            field_value = kpi[field_name]
            if not field_value:
                if required:
                    raise ValidationError(
                        _('"%(field_name)s" field is required for non custom aggregation.', field_name=field_name))
                continue
            if field_value.id not in (available_fields := allowed_fields_by_model.get(kpi.res_model_id.id, {})):
                raise ValidationError(
                    _('Invalid "%(field_name)s" value. Expecting one of %(fields)s (actual: %(actual_field)s).',
                      field_name=field_name,
                      fields=', '.join(available_fields.values()),
                      actual_field=field_value.name))

    @api.constrains('agg_mode', 'agg_custom')
    def _check_agg_custom(self):
        for kpi in self:
            if kpi.agg_mode != 'custom' or not kpi.agg_custom:
                continue
            prev_agg_format = None
            for __, __, (start, end) in self.env['digest.kpi']._get_timeframes():
                value = kpi.agg_custom.with_context(
                    companies=self.env.company, start=start, end=end).run()
                format_valid = (isinstance(value, tuple) and len(value) == 2
                                and isinstance(value[0], dict)
                                and isinstance(value[1], str))
                if not format_valid:
                    raise ValidationError(_("The custom aggregation function must return a tuple(dict, str)."))
                value_by_company = value[0]
                if self.env.company.id not in value_by_company:
                    raise ValidationError(_("The custom aggregation function must return value per company."))
                if not isinstance(value_by_company.get(self.env.company.id), (int, float)):
                    raise ValidationError(_("The custom aggregation function must return numeric value per company."))
                agg_format = value[1]
                allowed_formats = ['integer', 'float', 'monetary']
                if agg_format not in allowed_formats:
                    raise ValidationError(_("The format must be one of the following values: %(allowed_formats)s.",
                                      allowed_formats=', '.join(allowed_formats)))
                if prev_agg_format and prev_agg_format != agg_format:
                    raise ValidationError(_("Aggregation custom code must always return the same format."))
                prev_agg_format = agg_format

    @api.constrains('agg_mode', 'res_model_id', 'domain')
    def _check_domain(self):
        for kpi in self:
            if not kpi.domain or kpi.agg_mode != 'custom' or not kpi.res_model_id:
                continue
            try:
                self.env[kpi.res_model_id.model].search(literal_eval(kpi.domain))
            except (ValueError, SyntaxError):
                raise ValidationError(_('Invalid Domain.'))

    @api.model_create_multi
    def create(self, vals_list):
        kpis = super().create(vals_list)
        kpis.sync_agg_custom(vals_list)
        return kpis

    def write(self, vals):
        res = super().write(vals)
        self.sync_agg_custom(list(repeat(vals, len(self))))
        return res

    def unlink(self):
        agg_customs = self.agg_custom
        res = super().unlink()
        agg_customs.unlink()
        return res

    def sync_agg_custom(self, vals_list):
        to_create = []
        to_delete = self.env['digest.kpi']
        for kpi, vals in zip(self, vals_list):
            if kpi.agg_mode == 'custom':
                name = f"Kpi: {kpi.name or ''}"
                if not kpi.agg_custom:
                    to_create.append(
                        (kpi, {
                            'name': name,
                            'model_id': kpi.res_model_id.id,
                            'state': 'code',
                            'code': kpi.agg_custom_code,
                        }))
                elif vals.get('agg_custom_code') or vals.get('name'):
                    kpi.agg_custom.code = kpi.agg_custom_code
                    kpi.agg_custom.name = name
            elif kpi.agg_custom:
                to_delete |= kpi
        for (kpi, __), agg_custom in zip(to_create, self.env['ir.actions.server'].create(
                [vals for __, vals in to_create])):
            kpi.agg_custom = agg_custom
        agg_customs = to_delete.agg_custom
        to_delete.agg_custom = False  # To avoid cascade deletion
        agg_customs.unlink()

    def action_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Edit Kpi"),
            'res_model': 'digest.kpi',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'res_id': self.id,
        }

    def action_remove_kpi_from_digest(self):
        self.ensure_one()
        if self.env.context.get('active_model') != 'digest.digest.kpi':
            return
        self.env['digest.digest.kpi'].browse(self.env.context.get('active_id')).action_remove_kpi_from_digest()

    def action_delete(self):
        self.ensure_one()
        self.unlink()

    @api.model
    def _get_timeframes(self):
        start_datetime = fields.Datetime.now()
        return [
            (
                'value_last_24_hours',
                (start_datetime + relativedelta(days=-2), start_datetime + relativedelta(days=-1)),
                (start_datetime + relativedelta(days=-1), start_datetime),
            ),
            (
                'value_last_7_days',
                (start_datetime + relativedelta(weeks=-2), start_datetime + relativedelta(weeks=-1)),
                (start_datetime + relativedelta(weeks=-1), start_datetime),
            ),
            (
                'value_last_30_days',
                (start_datetime + relativedelta(months=-2), start_datetime + relativedelta(months=-1)),
                (start_datetime + relativedelta(months=-1), start_datetime),
            )
        ]

    def _calculate_values_by_company(self, companies):
        DigestKpi = self.env['digest.kpi']
        time_frames = self._get_timeframes()
        values_by_kpi_id_by_company_id = {company.id: {} for company in companies}
        for kpi in self:
            has_error = False
            error_msg = None
            try:
                for field, (prev_start, prev_end), (start, end) in time_frames:
                    if kpi.agg_mode == 'custom':
                        previous_by_company, agg_format = kpi.agg_custom.with_context(
                            companies=companies, start=prev_start, end=prev_end).run()
                        current_by_company, agg_format2 = kpi.agg_custom.with_context(
                            companies=companies, start=start, end=end).run()
                        if agg_format != agg_format2:
                            has_error = True  # Aggregation custom code must always return the same format.
                            error_msg = f"Format missmatch {agg_format} != {agg_format2}"
                            break
                    else:
                        previous_by_company = kpi._calculate_non_custom_kpi(
                            company_ids=companies.ids, start=prev_start, end=prev_end)
                        current_by_company = kpi._calculate_non_custom_kpi(
                            company_ids=companies.ids, start=start, end=end)
                        # Determine format from the field type/agg_mode
                        if kpi.agg_mode == 'count':
                            agg_format = 'integer'
                        else:
                            field_info = self.env[kpi.res_model_id.model]._fields.get(kpi.agg_field.name)
                            agg_format = field_info.type
                            if kpi.agg_mode in ('avg', 'neg_avg') and agg_format == 'integer':
                                agg_format = 'float'

                    for company in companies:
                        current_value = current_by_company[company.id]
                        values_by_kpi_id_by_company_id[company.id].setdefault(kpi.id, {})[field] = {
                            'value': DigestKpi._format_value(current_value, agg_format, company),
                            'margin': DigestKpi._get_margin_value(current_value, previous_by_company[company.id]),
                        }
            except Exception as e:
                error_msg = str(e)
                has_error = True
            if has_error:
                for company in companies:
                    values_by_kpi_id_by_company_id[company.id][kpi.id] = {
                        'error': True,
                        'error_msg': error_msg,
                    }
        return values_by_kpi_id_by_company_id

    # ------------------------------------------------------------
    # FORMATTING / TOOLS
    # ------------------------------------------------------------

    def _calculate_non_custom_kpi(self, company_ids, start, end):
        """Generic method that computes the KPI on a given model."""
        self.ensure_one()
        domain = [
            (self.date_field.name, '>=', start),
            (self.date_field.name, '<', end),
        ]

        if self.domain:
            domain = expression.AND([domain, literal_eval(self.domain)])

        if not self.company_field and self.agg_mode == 'count':
            value = self.env[self.res_model_id.model].search_count(domain)
            return {company_id: value for company_id in company_ids}

        if self.company_field:
            domain = expression.AND([
                domain,
                ['|', (self.company_field.name, 'in', company_ids), (self.company_field.name, '=', False)]])

        if self.agg_mode.startswith('neg_'):
            operation, sign = self.agg_mode.replace('neg_', ''), -1
        else:
            operation, sign = self.agg_mode, 1
        values = self.env[self.res_model_id.model]._read_group(
            domain=domain,
            groupby=[self.company_field.name] if self.company_field else [],
            aggregates=[f'{self.agg_field.name}:{operation}'] if self.agg_mode != 'count' else ['__count'],
        )

        if not self.company_field:
            agg_value = values[0][0]
            return {company_id: agg_value for company_id in company_ids}

        results = {company.id: agg for company, agg in values}
        missing_values = {company_id: 0 for company_id in company_ids if company_id not in results}
        # TODO: check if we need to add no company value to all companies kpi
        no_company_value = results.get(False, 0)
        return {
            company_id: sign * (value + no_company_value)
            for company_id, value in {**results, **missing_values}.items()
        }

    def _get_kpi_data(self, values_by_kpi):
        kpi_fields = [
            ('value_last_24_hours', _('Last 24 hours')),
            ('value_last_7_days', _('Last 7 days')),
            ('value_last_30_days', _('Last 30 days')),
        ]
        results = []
        for kpi in self:
            kpi_data = {
                'kpi_name': kpi.name,
                'kpi_action_url': kpi.action_url,
                'kpi_icon_url': kpi.icon_url,
            }
            values = values_by_kpi[kpi.id]
            for field_idx, (field, subtitle) in enumerate(kpi_fields):
                kpi_data[f'kpi_col{field_idx + 1}'] = {
                    'value': values[field]['value'],
                    'margin': values[field]['margin'],
                    'col_subtitle': subtitle,
                }
            results.append(kpi_data)
        return results

    @api.model
    def _get_margin_value(self, value, previous_value=0.0):
        margin = 0.0
        if (value != previous_value) and (value != 0.0 and previous_value != 0.0):
            margin = float_round((float(value - previous_value) / previous_value or 1) * 100, precision_digits=2)
        return margin

    @api.model
    def _format_value(self, value, format_type, company):
        """Format the value for the company with the given format_type (monetary/float/integer)."""
        if format_type == 'monetary':
            return self._format_currency_amount(tools.misc.format_decimalized_amount(value), company.currency_id)
        elif format_type == 'float':
            return "%.2f" % value
        elif format_type == 'integer':
            return str(int(value))
        else:
            raise ProgrammingError(f"Invalid format {format_type}")

    @api.model
    def _format_currency_amount(self, amount, currency_id):
        pre = currency_id.position == 'before'
        symbol = '{symbol}'.format(symbol=currency_id.symbol or '')
        return '{pre}{0}{post}'.format(amount, pre=symbol if pre else '', post=symbol if not pre else '')
