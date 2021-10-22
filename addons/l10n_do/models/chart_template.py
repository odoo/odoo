# coding: utf-8
# Copyright 2016 iterativo (https://www.iterativo.do) <info@iterativo.do>

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('do', 'account.journal')
    def _get_do_account_journal(self):
        return {
            "caja_chica": {
                'name': _('Caja Chica'),
                'type': 'cash',
                'sequence': 10,
            },
            "cheques_clientes": {
                'name': _('Cheques Clientes'),
                'type': 'cash',
                'sequence': 10,
            },
            "gasto": {
                'type': 'purchase',
                'name': _('Gastos No Deducibles'),
                'code': 'GASTO',
                'show_on_dashboard': True,
            },
            "cxp": {
                'type': 'purchase',
                'name': _('Migración CxP'),
                'code': 'CXP',
                'show_on_dashboard': True,
            },
            "cxc": {
                'type': 'sale',
                'name': _('Migración CxC'),
                'code': 'CXC',
                'show_on_dashboard': True,
            },
        }
