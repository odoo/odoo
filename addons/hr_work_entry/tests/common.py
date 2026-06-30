# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo.fields import Date
from odoo.tests.common import TransactionCase


class TestWorkEntryBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.tz = 'Europe/Brussels'
        cls.env.ref('resource.resource_calendar_std').tz = 'Europe/Brussels'

        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })

        # I create a new employee "Richard"
        cls.richard_emp = cls.env['hr.employee'].create({
            'name': 'Richard',
            'sex': 'male',
            'birthday': '1984-05-01',
            'country_id': cls.env.ref('base.be').id,
            'department_id': cls.dep_rd.id,
            'wage': 5000.0,
            'date_version': Date.to_date('2018-01-01'),
            'contract_date_start': Date.to_date('2018-01-01'),
            'contract_date_end': Date.today() + relativedelta(years=2),
        })

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Extra attendance',
            'is_leave': False,
            'code': 'WORKTEST200',
        })

        cls.work_entry_type_unpaid = cls.env['hr.work.entry.type'].create({
            'name': 'Unpaid Time Off',
            'is_leave': True,
            'code': 'LEAVETEST300',
        })

        cls.work_entry_type_leave = cls.env['hr.work.entry.type'].create({
            'name': 'Time Off',
            'is_leave': True,
            'code': 'LEAVETEST100'
        })

    def create_work_entry(self, start, stop, work_entry_type=None):
        work_entry_type = work_entry_type or self.work_entry_type
        return self.create_work_entries([(start, stop, work_entry_type)])

    def create_work_entries(self, intervals):
        default_work_entry_type = self.work_entry_type
        create_vals = []
        for interval in intervals:
            start = interval[0]
            stop = interval[1]
            work_entry_type = interval[2] if len(interval) == 3\
                else default_work_entry_type
            create_vals.append({
                'version_id': self.richard_emp.version_ids[0].id,
                'name': 'Work entry %s-%s' % (start, stop),
                'date_start': start,
                'date_stop': stop,
                'employee_id': self.richard_emp.id,
                'work_entry_type_id': work_entry_type.id,
            })
        create_vals = self.env['hr.version']._generate_work_entries_postprocess(create_vals)
        return self.env['hr.work.entry'].create(create_vals)
