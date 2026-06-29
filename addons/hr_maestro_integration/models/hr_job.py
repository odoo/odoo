# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    maestro_app_profile = fields.Selection([
        ('colaborador', 'Colaborador / Plantonista'),
        ('gestor', 'Encarregado de Unidade (Gestor)'),
        ('supervisor', 'Supervisor Operacional'),
        ('dono', 'Diretor Executivo'),
        ('financeiro', 'Diretor Financeiro'),
        ('psicologo', 'Psicólogo Organizacional'),
    ], string='Perfil no app Maestro',
        help='Define qual tela do aplicativo Maestro (PWA) os funcionários '
             'com este cargo acessam ao fazer login. Cargos sem perfil '
             'definido não conseguem entrar no app.')
