from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from .recurrence_utils import (
    RRULE_TYPE_SELECTION, RRULE_TYPE_SELECTION_UI, END_TYPE_SELECTION,
    MONTH_BY_SELECTION, WEEKDAY_SELECTION, BYDAY_SELECTION
)


class RecurrenceInstanceMixin(models.AbstractModel):
    _name = 'mail.recurrence.instance.mixin'
    _description = 'Recurrence UI'

    rrule = fields.Char('Recurrent Rule', compute='_compute_recurrence', readonly=False, store=False)
    rrule_type_ui = fields.Selection(RRULE_TYPE_SELECTION_UI, string='Repeat', compute="_compute_rrule_type_ui", readonly=False, store=False)
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, string='Recurrence', compute='_compute_recurrence', readonly=False, store=False)
    recurrence_tz = fields.Selection(_tz_get, string='Timezone', compute='_compute_recurrence', readonly=False, store=False)
    end_type = fields.Selection(END_TYPE_SELECTION, string='Recurrence Termination', compute='_compute_recurrence', readonly=False, store=False)
    interval = fields.Integer(string='Repeat On', compute='_compute_recurrence', readonly=False, store=False)
    count = fields.Integer(string='Number of Repetitions', compute='_compute_recurrence', readonly=False, store=False)

    mon = fields.Boolean(compute='_compute_recurrence', readonly=False, store=False)
    tue = fields.Boolean(compute='_compute_recurrence', readonly=False, store=False)
    wed = fields.Boolean(compute='_compute_recurrence', readonly=False, store=False)
    thu = fields.Boolean(compute='_compute_recurrence', readonly=False, store=False)
    fri = fields.Boolean(compute='_compute_recurrence', readonly=False, store=False)
    sat = fields.Boolean(compute='_compute_recurrence', readonly=False, store=False)
    sun = fields.Boolean(compute='_compute_recurrence', readonly=False, store=False)

    month_by = fields.Selection(MONTH_BY_SELECTION, string='Option', compute='_compute_recurrence', readonly=False, store=False)
    day = fields.Integer('Date of month', compute='_compute_recurrence', readonly=False, store=False)
    weekday = fields.Selection(WEEKDAY_SELECTION, compute='_compute_recurrence', readonly=False, store=False)
    byday = fields.Selection(BYDAY_SELECTION, string="By day", compute='_compute_recurrence', readonly=False, store=False)
    until = fields.Date(compute='_compute_recurrence', readonly=False, store=False)
    is_recurring_field_name = fields.Char(compute='_compute_is_recurring_field_name')

    def _compute_is_recurring_field_name(self):
        field_name = self._get_is_recurring_field_name()
        for record in self:
            record.is_recurring_field_name = field_name

    @api.model
    def _get_recurrence_rule_model(self):
        return f"{self._name}.recurrence"

    @api.model
    def _get_recurrence_record_field_name(self):
        return 'recurrence_id'

    @api.model
    def _get_is_recurring_field_name(self):
        return 'recurrency'

    @api.model
    def _get_recurrence_unit_field_name(self):
        return 'rrule_type_ui'

    @api.model
    def _get_recurrence_depends(self):
        return [
            self._get_recurrence_record_field_name(),
            self._get_is_recurring_field_name(),
            self._get_recurrence_unit_field_name(),
        ]

    @api.model
    def _get_recurrence_ui_fields(self):
        """ Fields read by the recurrence widget. """
        return (self._get_recurrent_fields() - {'rrule', 'recurrence_tz'}) | {'rrule_type_ui', 'is_recurring_field_name'}

    @api.model
    def _get_recurrent_fields(self):
        return {
            'rrule_type', 'recurrence_tz', 'end_type', 'interval', 'count', 'rrule',
            'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
            'month_by', 'day', 'weekday', 'byday', 'until'
        }

    def _read_recurrence_rule_values(self, field_names):
        """ Read the given fields of the recurrence rules of the records, in one query.

        Users allowed to read a record may not be allowed to read its rule (e.g. portal
        users on project tasks), so only these fields are read, as superuser, and only
        their values are returned.

        :return: {rule_id: {field_name: value}}
        """
        rules = self[self._get_recurrence_record_field_name()]._origin
        if not rules:
            return {}
        return {
            values.pop('id'): values
            for values in rules.sudo().read(list(field_names), load=False)
        }

    @api.depends(lambda self: self._get_recurrence_depends())
    def _compute_recurrence(self):
        recurrence_fields = self._get_recurrent_fields()
        false_values = {field: False for field in recurrence_fields}
        defaults = self.env[self._get_recurrence_rule_model()].default_get(list(recurrence_fields))
        rule_values_by_id = self._read_recurrence_rule_values(recurrence_fields)

        for record in self:
            is_recurring = record[record._get_is_recurring_field_name()]
            rule_id = record[record._get_recurrence_record_field_name()]._origin.id

            if is_recurring:
                current_rrule = (record.rrule_type if record.rrule_type_ui == "custom" else record.rrule_type_ui)
                record.update(defaults)
                occurrence_values = record._get_recurrence_defaults()
                rrule_values = {}
                if rule_id:
                    rrule_values = {
                        field: value
                        for field, value in rule_values_by_id[rule_id].items()
                        if value
                    } or dict(defaults)
                rrule_values['rrule_type'] = current_rrule or rrule_values.get('rrule_type') or defaults.get('rrule_type')
                record.update({**false_values, **defaults, **occurrence_values, **rrule_values})
            else:
                record.update(false_values)

    def _get_recurrence_defaults(self):
        return {}

    @api.depends(lambda self: [self._get_is_recurring_field_name(), self._get_recurrence_record_field_name()])
    def _compute_rrule_type_ui(self):
        rule_values_by_id = self._read_recurrence_rule_values(['interval', 'rrule_type'])
        for record in self:
            is_recurring = record[record._get_is_recurring_field_name()]
            rule_id = record[record._get_recurrence_record_field_name()]._origin.id
            if is_recurring:
                if rule_id:
                    rule_values = rule_values_by_id[rule_id]
                    record.rrule_type_ui = 'custom' if rule_values['interval'] != 1 else rule_values['rrule_type']
                else:
                    record.rrule_type_ui = record.rrule_type or 'weekly'
            else:
                record.rrule_type_ui = False

    def _get_recurrence_rule_values(self):
        """ Return the values to create a recurrence rule from this record.

        The recurrence fields are only computed on recurring records: for a record that is
        not recurring (yet), use the default values of the rule, as the form would.
        The rrule is left out, the rule computes it from the other fields.
        """
        self.ensure_one()
        field_names = self._get_recurrent_fields() - {'rrule'}
        if not self[self._get_is_recurring_field_name()]:
            return {
                **self.env[self._get_recurrence_rule_model()].default_get(list(field_names)),
                **self._get_recurrence_defaults(),
            }
        return {field: self[field] for field in field_names}

    def _create_recurrence_rule(self, **kwargs):
        self.ensure_one()
        values = self._get_recurrence_rule_values()
        values.update(kwargs)
        RuleModel = self.env[self._get_recurrence_rule_model()]
        return RuleModel.create(values)
