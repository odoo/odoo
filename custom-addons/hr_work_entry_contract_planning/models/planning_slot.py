#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, models

def batch(iterable, batch_size):
    l = len(iterable)
    for n in range(0, l, batch_size):
        yield iterable[n:min(n + batch_size, l)]

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    def _create_work_entries(self):
        # Similar to `_create_work_entries` for attendances but this function assumes big batches
        # (due to the publish button that published all slots)
        # Also note that slots are assumed to stay as is after being published, any other change will need a
        # full work entry regeneration.
        self = self.filtered(lambda s: s.employee_id)
        if not self:
            return
        # The procedure for creating a work entry within an already generated period
        # is more complicated for planning slots than for leaves because leaves override
        # attendance periods, here we are not able to just archive work entries we do not want
        # etc...
        # We will instead archive all work entries that are touched by the current planning slot's period
        # (slots don't have an overlap constraint), and regenerate all work entries that were covered by them.
        # Since all we need is already in the database we can use that query to have better performance.
        self.flush_model(['start_datetime', 'end_datetime', 'employee_id'])
        self.env['hr.contract'].flush_model([
            'employee_id', 'state', 'work_entry_source',
            'date_start', 'date_end', 'date_generated_from', 'date_generated_to'
        ])
        self.env['hr.work.entry'].flush_model(['employee_id', 'date_start', 'date_stop'])
        self.env.cr.execute("""
            SELECT slot.id as id,
                   ARRAY_AGG(DISTINCT contract.id) as contract_ids,
                   ARRAY_AGG(DISTINCT hwe.id) as work_entry_ids,
                   COALESCE(MIN(hwe.date_start), slot.start_datetime) as start,
                   COALESCE(MAX(hwe.date_stop), slot.end_datetime) as stop
              FROM planning_slot slot
              JOIN hr_contract contract
                ON contract.employee_id = slot.employee_id AND
                   contract.state in ('open', 'close') AND
                   contract.work_entry_source = 'planning' AND
                   contract.date_generated_from < slot.end_datetime AND
                   contract.date_generated_to > slot.start_datetime AND
                   contract.date_start <= slot.end_datetime AND
                   (contract.date_end IS NULL OR
                    contract.date_end >= slot.start_datetime)
         LEFT JOIN hr_work_entry hwe
                ON hwe.employee_id = slot.employee_id AND
                   hwe.date_start <= slot.end_datetime AND
                   hwe.date_stop >= slot.start_datetime
             WHERE slot.id in %s
          GROUP BY slot.id
        """, [tuple(self.ids)])
        query_result = self.env.cr.dictfetchall()
        # Group by period to generate to profit from batching
        # Contains [(start, stop)] = [contract_ids]
        periods_to_generate = defaultdict(list)
        work_entries_to_archive = []
        for row in query_result:
            periods_to_generate[(row['start'], row['stop'])].extend(row['contract_ids'])
            if any(row['work_entry_ids']):
                work_entries_to_archive.extend(row['work_entry_ids'])
        self.env['hr.work.entry'].sudo().browse(work_entries_to_archive).write({'active': False})
        work_entries_vals_list = []
        for period, contract_ids in periods_to_generate.items():
            if not contract_ids:
                continue
            contracts = self.env['hr.contract'].sudo().browse(contract_ids)
            work_entries_vals_list.extend(contracts._get_work_entries_values(period[0], period[1]))
        self.env['hr.work.entry'].sudo().create(work_entries_vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.filtered(lambda s: s.state == 'published')._create_work_entries()
        return res

    def write(self, vals):
        state = vals.get('state')
        concerned_slots = self.filtered(lambda s: s.state != state) if state\
            else self.env['planning.slot']
        res = super().write(vals)
        concerned_slots._create_work_entries()
        return res

    def unlink(self):
        # Archive linked work entries upon deleting slots
        self.env['hr.work.entry'].sudo().search([('planning_slot_id', 'in', self.ids)]).write({'active': False})
        return super().unlink()
