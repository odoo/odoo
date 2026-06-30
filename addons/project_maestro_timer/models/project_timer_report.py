# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProjectTimerReport(models.Model):
    """Read-only SQL view for the efficacy report (horas por funcionário / semana / mês / ano)."""
    _name = 'project.timer.report'
    _description = 'Relatório de Eficácia de Tarefas'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string='Data', readonly=True)
    week = fields.Char(string='Semana', readonly=True)
    month = fields.Char(string='Mês', readonly=True)
    year = fields.Integer(string='Ano', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Funcionário', readonly=True)
    department_id = fields.Many2one('hr.department', string='Departamento', readonly=True)
    project_id = fields.Many2one('project.project', string='Projeto', readonly=True)
    task_id = fields.Many2one('project.task', string='Tarefa', readonly=True)
    unit_amount = fields.Float(string='Horas trabalhadas', readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS project_timer_report;
            CREATE VIEW project_timer_report AS
            SELECT
                aal.id                                                 AS id,
                aal.date                                               AS date,
                TO_CHAR(aal.date, 'IYYY-IW')                          AS week,
                TO_CHAR(aal.date, 'YYYY-MM')                          AS month,
                EXTRACT(YEAR FROM aal.date)::INTEGER                  AS year,
                aal.employee_id                                        AS employee_id,
                emp.department_id                                      AS department_id,
                aal.project_id                                         AS project_id,
                aal.task_id                                            AS task_id,
                aal.unit_amount                                        AS unit_amount
            FROM   account_analytic_line  aal
            JOIN   hr_employee            emp ON emp.id = aal.employee_id
            WHERE  aal.project_id IS NOT NULL
        """)
