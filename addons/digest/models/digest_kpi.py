# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from sqlite3 import ProgrammingError

from dateutil.relativedelta import relativedelta
from itertools import repeat

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_round


ODOO_ICONS_CDN_URL = 'https://download.odoocdn.com/icons'
KPI_FIELDS = ['value_last_24_hours', 'value_last_7_days', 'value_last_30_days']


class DigestKpi(models.Model):
    _name = 'digest.kpi'
    _description = 'Kpi'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(required=True, default=0)
    res_model_id = fields.Many2one('ir.model', 'Model', ondelete='cascade', required=True)
    company_field = fields.Char('Company Field', default='company_id', required=False)

    # Standard computation
    agg_mode = fields.Selection(
        [('sum', 'Sum'), ('avg', 'Average'), ('count', 'Count'), ('custom', 'Custom')],
        default='sum', string='Aggregation Mode', required=True)
    agg_field = fields.Char('Aggregation Field', required=False)
    date_field = fields.Char('Date Field', required=False)
    domain = fields.Char('Domain', required=False)

    # Custom computation
    agg_custom = fields.Many2one('ir.actions.server', required=False, ondelete='cascade')
    agg_custom_code = fields.Text(
        "Custom Code", compute="_compute_agg_custom_code", store=True, readonly=False
    )

    # Action
    action_id = fields.Many2one('ir.actions.actions', string="Action", ondelete="set null")
    action_menu_root_id = fields.Many2one('ir.ui.menu', string="Action Menu Root", ondelete="set null")

    # App
    module_id = fields.Many2one('ir.module.module', 'Module', ondelete='set null')
    icon_url = fields.Char('Icon URL', compute='_compute_icon_url', compute_sudo=True)

    # Computed values
    value_last_24_hours = fields.Char(compute_sudo=True, compute='_compute_values')
    value_last_7_days = fields.Char(compute_sudo=True, compute='_compute_values')
    value_last_30_days = fields.Char(compute_sudo=True, compute='_compute_values')

    value_last_24_hours_margin = fields.Float(compute_sudo=True, compute='_compute_values')
    value_last_7_days_margin = fields.Float(compute_sudo=True, compute='_compute_values')
    value_last_30_days_margin = fields.Float(compute_sudo=True, compute='_compute_values')

    has_compute_error = fields.Boolean(compute_sudo=True, compute='_compute_values')

    # Security
    group_ids = fields.Many2many(
        'res.groups', string='Allowed Groups',
        help="To read this kpi, user needs to be at least in one of these groups.")

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
        for kpi in self:
            if not kpi.date_field or kpi.agg_mode == 'custom':
                continue
            allowed_field = {
                field.name
                for field_name, field in self.env[kpi.res_model_id.model]._fields.items()
                if isinstance(field, fields.Date) or isinstance(field, fields.Datetime)
            }
            if kpi.date_field not in allowed_field:
                if allowed_field:
                    raise ValidationError(
                        _('Date Field must be one of the following values: %s.', ', '.join(allowed_field)))
                else:
                    raise ValidationError(
                        _('There are no date field in the model "%s" for Date Field.', kpi.res_model_id.name))

    @api.constrains('agg_mode', 'res_model_id', 'company_field')
    def _check_company_field(self):
        for kpi in self:
            if not kpi.company_field or kpi.agg_mode == 'custom':
                continue
            allowed_field = {
                field.name
                for field_name, field in self.env[kpi.res_model_id.model]._fields.items()
                if field.type == 'many2one' and field.comodel_name == 'res.company'
            }
            if kpi.company_field not in allowed_field:
                if allowed_field:
                    raise ValidationError(
                        _('Company Field must be one of the following values: %s.', ', '.join(allowed_field)))
                else:
                    raise ValidationError(
                        _('There are no company field in the model "%s" for Company Field.', kpi.res_model_id.name))

    @api.constrains('agg_field', 'agg_mode', 'res_model_id')
    def _check_agg_field(self):
        for kpi in self:
            if kpi.agg_mode not in ('sum', 'avg'):
                continue
            allowed_field = {
                field.name
                for field_name, field in self.env[kpi.res_model_id.model]._fields.items()
                if field.type in ('integer', 'float', 'monetary')
            }
            agg_field, __ = kpi._get_agg_field_and_sign()
            if agg_field not in allowed_field:
                if allowed_field:
                    raise ValidationError(
                        _('Aggregation Field must be one of the following values: %s.', ', '.join(allowed_field)))
                else:
                    raise ValidationError(
                        _('There are no field in the model "%s" that could be use as Aggregation Field.',
                          kpi.res_model_id.name))

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

    @api.depends_context("company")
    def _compute_values(self):
        company = self.env.company
        values_by_kpi_id_by_company_id = self._calculate_values_by_company(company)
        values_by_kpi = values_by_kpi_id_by_company_id[company.id]
        for kpi in self:
            kpi.has_compute_error = values_by_kpi[kpi.id].get('error', False)
            if kpi.has_compute_error:
                for field in KPI_FIELDS:
                    kpi[field] = '-'
                    kpi[f'{field}_margin'] = 0
            else:
                values_by_field = values_by_kpi[kpi.id]
                for field in KPI_FIELDS:
                    kpi[field] = values_by_field[field]['value']
                    kpi[f'{field}_margin'] = values_by_field[field]['margin']

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
        time_frames = self._get_timeframes()
        values_by_kpi_id_by_company_id = {company.id: {} for company in companies}
        for kpi in self:
            try:
                for field, (prev_start, prev_end), (start, end) in time_frames:
                    if kpi.agg_mode == 'custom':
                        previous_by_company, agg_format = kpi.agg_custom.with_context(
                            companies=companies, start=prev_start, end=prev_end).run()
                        current_by_company, agg_format2 = kpi.agg_custom.with_context(
                            companies=companies, start=start, end=end).run()
                        if agg_format != agg_format2:
                            raise ValidationError(_("Aggregation custom code must always return the same format."))
                    else:
                        previous_by_company = kpi._calculate_non_custom_kpi(
                            company_ids=companies.ids, start=prev_start, end=prev_end)
                        current_by_company = kpi._calculate_non_custom_kpi(
                            company_ids=companies.ids, start=start, end=end)
                        # Determine format from the field type/agg_mode
                        if kpi.agg_mode == 'count':
                            agg_format = 'integer'
                        else:
                            agg_field, __ = kpi._get_agg_field_and_sign()
                            field_info = self.env[kpi.res_model_id.model]._fields.get(agg_field)
                            agg_format = field_info.type
                            if kpi.agg_mode == 'avg' and agg_format == 'integer':
                                agg_format = 'float'

                    for company in companies:
                        previous_value = previous_by_company[company.id]
                        current_value = current_by_company[company.id]

                        margin = kpi._get_margin_value(current_value, previous_value)
                        if agg_format == 'monetary':
                            converted_amount = tools.misc.format_decimalized_amount(current_value)
                            current_value = kpi._format_currency_amount(converted_amount, company.currency_id)
                        elif agg_format == 'float':
                            current_value = "%.2f" % current_value
                        elif agg_format == 'integer':
                            current_value = str(int(current_value))
                        else:
                            raise ProgrammingError(f"Invalid format {agg_format}")

                        values_by_kpi_id_by_company_id[company.id].setdefault(kpi.id, {})[field] = {
                            'value': current_value,
                            'margin': margin,
                        }
            except:
                for company in companies:
                    values_by_kpi_id_by_company_id[company.id][kpi.id] = {
                        'error': True,
                    }
        return values_by_kpi_id_by_company_id

    # ------------------------------------------------------------
    # FORMATTING / TOOLS
    # ------------------------------------------------------------

    def _get_agg_field_and_sign(self):
        self.ensure_one()
        if not self.agg_field:
            return False, 1
        if self.agg_field.startswith('-'):
            return self.agg_field[1:], -1
        return self.agg_field, 1

    def _calculate_non_custom_kpi(self, company_ids, start, end):
        """Generic method that computes the KPI on a given model."""
        self.ensure_one()
        domain = [
            (self.date_field, '>=', start),
            (self.date_field, '<', end),
        ]

        if self.domain:
            domain = expression.AND([domain, literal_eval(self.domain)])

        if not self.company_field and self.agg_mode == 'count':
            value = self.env[self.res_model_id.model].search_count(domain)
            return {company_id: value for company_id in company_ids}

        if self.company_field:
            domain = expression.AND([domain,
                                     ['|', (self.company_field, 'in', company_ids), (self.company_field, '=', False)]])

        agg_field, sign = self._get_agg_field_and_sign()
        values = self.env[self.res_model_id.model]._read_group(
            domain=domain,
            groupby=[self.company_field] if self.company_field else [],
            aggregates=[f'{agg_field}:{self.agg_mode}'] if self.agg_mode != 'count' else ['__count'],
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
            kpi_action = kpi.action_id.xml_id or kpi.action_id.id
            if kpi_action and kpi.action_menu_root_id:
                kpi_action = f'{kpi_action}?menu_id={kpi.action_menu_root_id.id}'
            kpi_data = {
                'kpi_name': kpi.name,
                'kpi_action': kpi_action,
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
            margin = float_round((float(value-previous_value) / previous_value or 1) * 100, precision_digits=2)
        return margin

    @api.model
    def _format_currency_amount(self, amount, currency_id):
        pre = currency_id.position == 'before'
        symbol = u'{symbol}'.format(symbol=currency_id.symbol or '')
        return u'{pre}{0}{post}'.format(amount, pre=symbol if pre else '', post=symbol if not pre else '')
