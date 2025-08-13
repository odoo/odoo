# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields

_logger = logging.getLogger(__name__)


class BaseBrowsableObject:
    def __init__(self, vals_dict):
        self.__dict__["base_fields"] = ["base_fields", "dict"]
        self.dict = vals_dict

    def __getattr__(self, attr):
        return attr in self.dict and self.dict.__getitem__(attr) or 0.0

    def __setattr__(self, attr, value):
        _fields = self.__dict__["base_fields"]
        if attr in _fields:
            return super().__setattr__(attr, value)
        self.__dict__["dict"][attr] = value

    def __str__(self):
        return str(self.__dict__)


# These classes are used in the _get_payslip_lines() method
class BrowsableObject(BaseBrowsableObject):
    def __init__(self, employee_id, vals_dict, env):
        super().__init__(vals_dict)
        self.base_fields += ["employee_id", "env"]
        self.employee_id = employee_id
        self.env = env


class InputLine(BrowsableObject):
    """a class that will be used into the python code, mainly for
    usability purposes"""

    def sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute(
            """
            SELECT sum(amount) as sum
            FROM hr_payslip as hp, hr_payslip_input as pi
            WHERE hp.employee_id = %s AND hp.state = 'done'
            AND hp.date_from >= %s AND hp.date_to <= %s
            AND hp.id = pi.payslip_id AND pi.code = %s""",
            (self.employee_id, from_date, to_date, code),
        )
        return self.env.cr.fetchone()[0] or 0.0


class WorkedDays(BrowsableObject):
    """a class that will be used into the python code, mainly for
    usability purposes"""

    def _sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute(
            """
            SELECT sum(number_of_days) as number_of_days,
             sum(number_of_hours) as number_of_hours
            FROM hr_payslip as hp, hr_payslip_worked_days as pi
            WHERE hp.employee_id = %s AND hp.state = 'done'
            AND hp.date_from >= %s AND hp.date_to <= %s
            AND hp.id = pi.payslip_id AND pi.code = %s""",
            (self.employee_id, from_date, to_date, code),
        )
        return self.env.cr.fetchone()

    def sum(self, code, from_date, to_date=None):
        res = self._sum(code, from_date, to_date)
        return res and res[0] or 0.0

    def sum_hours(self, code, from_date, to_date=None):
        res = self._sum(code, from_date, to_date)
        return res and res[1] or 0.0


class Payslips(BrowsableObject):
    """a class that will be used into the python code, mainly for
    usability purposes"""

    def sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute(
            """SELECT sum(case when hp.credit_note = False then
            (pl.total) else (-pl.total) end)
                    FROM hr_payslip as hp, hr_payslip_line as pl
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND
                     hp.id = pl.slip_id AND pl.code = %s""",
            (self.employee_id, from_date, to_date, code),
        )
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0
