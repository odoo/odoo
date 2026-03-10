# Copyright (C) 2009  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class City(models.Model):
    """Este objeto persite todos os municípios relacionado a um estado.
    No Brasil é necesário em alguns documentos fiscais informar o código
    do IBGE dos município envolvidos na transação.
    """

    _inherit = "res.city"

    ibge_code = fields.Char(string="IBGE Code", size=7, index=True)
    siafi_code = fields.Char(string="SIAFI Code", size=4)
    anp_code = fields.Char(string="ANP Code", size=4)
