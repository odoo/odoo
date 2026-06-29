# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from .hr_job import MAESTRO_APP_PROFILES

CHECKLIST_TEMPLATES = {
    'colaborador': [
        ('abertura_login', 'Login no sistema (Termoplus ou Cloud Park)'),
        ('abertura_fundo', 'Conferir e registrar fundo de caixa'),
        ('abertura_uniforme', 'Uniforme e crachá em dia'),
        ('atendimento_sinistro', 'Protocolo de sinistro, se houver'),
        ('fechamento_caixa', 'Fechamento de caixa às 23h59'),
        ('fechamento_malote', 'Malote de RP conferido e lacrado'),
    ],
    'gestor': [
        ('equipe_presenca', 'Conferir presença da equipe do turno'),
        ('auditoria_online', 'Auditoria online do posto'),
        ('avaliacao_25d', 'Avaliação de equipe (ciclo 25 dias)'),
        ('malote_rp', 'Malote · RP conferido'),
    ],
    'supervisor': [
        ('postos_visita', 'Visita/checagem dos postos da regional'),
        ('malotes_rp', 'Malotes · RP consolidados'),
        ('kpis_revisao', 'Revisão de KPIs do dia'),
    ],
}


class HrMaestroChecklist(models.Model):
    _name = 'hr.maestro.checklist'
    _description = 'Checklist diário do app Maestro'
    _order = 'date desc, id desc'
    _rec_name = 'date'

    employee_id = fields.Many2one('hr.employee', string='Funcionário', required=True,
                                   index=True, ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', string='Departamento', store=True)
    date = fields.Date(string='Data', required=True, default=fields.Date.context_today)
    profile = fields.Selection(MAESTRO_APP_PROFILES, string='Perfil', required=True)
    item_ids = fields.One2many('hr.maestro.checklist.item', 'checklist_id', string='Itens')
    item_count = fields.Integer(string='Total de itens', compute='_compute_progress', store=True)
    done_count = fields.Integer(string='Itens concluídos', compute='_compute_progress', store=True)
    completion_rate = fields.Float(string='% concluído', compute='_compute_progress', store=True)

    _sql_constraints = [
        ('employee_date_uniq', 'unique(employee_id, date)',
         'Já existe um checklist deste funcionário nesta data.'),
    ]

    @api.depends('item_ids.done')
    def _compute_progress(self):
        for checklist in self:
            checklist.item_count = len(checklist.item_ids)
            checklist.done_count = len(checklist.item_ids.filtered('done'))
            checklist.completion_rate = (
                checklist.done_count / checklist.item_count if checklist.item_count else 0.0)

    @api.model
    def _get_or_create_today(self, employee):
        today = fields.Date.context_today(self)
        checklist = self.sudo().search([
            ('employee_id', '=', employee.id), ('date', '=', today)], limit=1)
        if checklist:
            return checklist
        profile = employee.maestro_app_profile
        template = CHECKLIST_TEMPLATES.get(profile, [])
        return self.sudo().create({
            'employee_id': employee.id,
            'date': today,
            'profile': profile,
            'item_ids': [
                (0, 0, {'code': code, 'label': label, 'sequence': sequence})
                for sequence, (code, label) in enumerate(template)
            ],
        })


class HrMaestroChecklistItem(models.Model):
    _name = 'hr.maestro.checklist.item'
    _description = 'Item de checklist diário do app Maestro'
    _order = 'sequence, id'

    checklist_id = fields.Many2one('hr.maestro.checklist', string='Checklist',
                                    required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequência', default=10)
    code = fields.Char(string='Código', required=True)
    label = fields.Char(string='Descrição', required=True)
    done = fields.Boolean(string='Concluído', default=False)
    done_at = fields.Datetime(string='Concluído em')

    def action_toggle(self):
        for item in self:
            new_done = not item.done
            item.write({'done': new_done, 'done_at': fields.Datetime.now() if new_done else False})
