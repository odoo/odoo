# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.sql import drop_view_if_exists, SQL


class l10nBeWorkEntryDailyBenefitReport(models.Model):
    """Generates a list of combination of dates, benefit name and employee_id.
       The list is created in accordance with:
       * The work entries currently in the system and the benefits associated with the work entry types.
       * The assumption that a work entry, even minimal (at least 1 hour) is enough to grant the benefit for
         that day.
    """
    _name = 'l10n_be.work.entry.daily.benefit.report'
    _description = 'Work Entry Related Benefit Report'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    day = fields.Date(readonly=True)
    benefit_name = fields.Char('Benefit Name', readonly=True)

    def init(self):
        drop_view_if_exists(self._cr, self._table)
        statement = SQL("""
            CREATE OR REPLACE VIEW %s AS (
                    SELECT work_entry.employee_id,
                           GREATEST(day_serie.day_serie, timezone(calendar.tz::text, work_entry.date_start::timestamp with time zone))::date AS day,
                           advantage.benefit_name,
                           ROW_NUMBER() OVER() AS id

                      FROM hr_work_entry work_entry
                      JOIN hr_contract contract ON work_entry.contract_id = contract.id
                                                AND work_entry.active
                                                AND work_entry.state::TEXT = ANY (ARRAY ['draft'::CHARACTER VARYING::TEXT, 'validated'::CHARACTER VARYING::TEXT])
                      JOIN resource_calendar calendar ON contract.resource_calendar_id = calendar.id
                      JOIN hr_work_entry_type ON work_entry.work_entry_type_id = hr_work_entry_type.id
                                              AND (hr_work_entry_type.meal_voucher = TRUE OR hr_work_entry_type.private_car = TRUE OR hr_work_entry_type.representation_fees = TRUE)
                CROSS JOIN LATERAL generate_series(date_trunc('day'::text, work_entry.date_start), date_trunc('day'::text, work_entry.date_stop), '1 day'::interval) day_serie(day_serie)
                CROSS JOIN LATERAL ( VALUES ('meal_voucher'::text,hr_work_entry_type.meal_voucher), ('private_car'::text,hr_work_entry_type.private_car), ('representation_fees'::text,hr_work_entry_type.representation_fees)) advantage(benefit_name, is_applicable)

                     WHERE advantage.is_applicable

                  GROUP BY 1,2,3

                    HAVING sum(date_part('hour'::text, LEAST(day_serie.day_serie + '1 day'::interval, timezone(calendar.tz::text, work_entry.date_stop::timestamp with time zone)) - GREATEST(day_serie.day_serie, timezone(calendar.tz::text, work_entry.date_start::timestamp with time zone)))) > 0::double precision
            );
        """, SQL.identifier(self._table))
        self._cr.execute(statement)
