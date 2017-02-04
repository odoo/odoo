# -*- coding: utf-8 -*-

from openerp import models, fields, api

class khf_project(models.Model):
     _name = 'khf.project'
    # _inherit = ['mail.thread']
     code = fields.Char('Idejos ID', size=32, required=True)
     akronimas = fields.Char('Akronimas', size=128, required=True, help="trumpinys")
     user_created =fields.Many2one('res.users', 'Sukure', required=False)
     cathedral = fields.Char("Skyrius/Katedra")
     create_date = fields.Date("Iskelimo data")
     status = fields.Char("Statusas")
     aim = fields.Text("Tikslas" , help="Tikslas turi atsakyti i klausima,kokio rezultato arba poveikio norima pasiekti")
     description = fields.Text("Aprasymas")
     partners = fields. Text("Partneriai")


     start_date = fields.Date("Pradzios data")
     end_date = fields.Date("Pabaigos data")

     budget= fields.Text("Biudzetas ir finansai")
     finanses = fields.Text("Finansavimo programa ")
     finanses_type= fields.Text("Finansavimo mechanizmas")
     intensity = fields.Text("Intensyvumas")
     asset = fields.Text("Turto isigijimas")

     documents = fields.Text("Papildomo dokumentai")
     active = fields.Boolean(string='Aktyvus', default=True)

     @api.depends('value')
     def _value_pc(self):
         self.value2 = float(self.value) / 100