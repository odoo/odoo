# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_split_name(self):
        self.ensure_one()
        names = re.sub(r"\([^()]*\)", "", self.name).strip().split()
        first_name = names[-1]
        last_name = ' '.join(names[:-1])
        return first_name, last_name
