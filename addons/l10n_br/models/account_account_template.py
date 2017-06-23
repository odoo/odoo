# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2017 KMEE INFORMATICA LTDA (https://www.kmee.com.br)


from __future__ import division, print_function, unicode_literals

from odoo import api, fields, models
from ..constantes import (
    TIPO_CONTA_CONTABIL,
)


class AccountAccountTemplate(models.Model):
    _inherit = 'account.account.template'

    is_brazilian_account = fields.Boolean(
        string=u'Is a Brazilian Account?',
    )
    # sped_empresa_id = fields.Many2one(
    #     comodel_name='sped.empresa',
    #     string='Empresa',
    # )
    parent_id = fields.Many2one(
        comodel_name='account.account.template',
        string='Conta superior',
        ondelete='restrict',
        index=True,
    )
    tipo = fields.Selection(
        selection=TIPO_CONTA_CONTABIL,
        string='Tipo',
    )

    @api.depends('company_id', 'currency_id', 'is_brazilian_account')
    def _compute_is_brazilian_account(self):
        for account in self:
            if account.company_id.country_id:
                if account.company_id.country_id.id == \
                        self.env.ref('base.br').id:
                    account.is_brazilian_account = True

                    #
                    # Brazilian accounts, by law, must always be in BRL
                    #
                    account.currency_id = self.env.ref('base.BRL').id

                    # if account.company_id.sped_empresa_id:
                    #     account.sped_empresa_id = \
                    #         account.company_id.sped_empresa_id.id

                    continue

            account.is_brazilian_account = False
    #
    # @api.onchange('sped_empresa_id')
    # def _onchange_sped_empresa_id(self):
    #     self.ensure_one()
    #     self.company_id = self.sped_empresa_id.company_id
    #
    # @api.model
    # def create(self, dados):
    #     if 'company_id' in dados:
    #         if 'sped_empresa_id' not in dados:
    #             company = self.env['res.company'].browse(dados['company_id'])
    #
    #             if company.sped_empresa_id:
    #                 dados['sped_empresa_id'] = company.sped_empresa_id.id
    #
    #     return super(AccountAccountTemplate, self).create(dados)
