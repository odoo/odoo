# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2017 KMEE INFORMATICA LTDA (https://www.kmee.com.br)


from __future__ import division, print_function, unicode_literals
from odoo import api, fields, models, _


class AccountAccountType(models.Model):

    _inherit = 'account.account.type'

    is_brazilian_account_type = fields.Boolean(
        string=u'Is a Brazilian Account?',
    )
    type = fields.Selection(
        selection_add=[
            ('ativo', 'Ativo'),  # natureza 01
            ('caixa', 'Caixa e bancos'),  # natureza 01
            ('receber', 'A receber'),  # natureza 01
            ('passivo', 'Passivo'),  # natureza 02
            ('receita', 'Receita'),  # natureza 09
            ('despesa', 'Despesa'),  # natureza 09
            ('custo', 'Custo'),  # natureza 09
            ('pagar', 'A pagar'),  # natureza 02
            ('resultado', 'Resultado'),  # natureza 04
            ('compensacao', 'Compensação'),  # natureza 05
            ('patrimonio', 'Patrimônio líquido'),  # natureza 03
            ('outras', 'Outras'),  # natureza 09
        ]
    )

    is_redutor = fields.Boolean(
        string='Redutor?',
        compute='_compute_is_redutor',
        store=True,
    )

    @api.depends('name')
    def _compute_is_redutor(self):
        for account_type in self:
            if account_type.name and (
                    account_type.name.startswith('(-)') or
                    account_type.name.startswith('( - )')):
                account_type.redutor = True
            account_type.redutor = False
