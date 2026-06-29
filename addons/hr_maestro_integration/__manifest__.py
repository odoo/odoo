# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Maestro Integration (NR-1 / Psychosocial Risk)',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Recebe eventos individuais da plataforma Maestro Intelligence e os integra ao perfil do funcionário',
    'description': """
Integração com a plataforma Maestro Intelligence
==================================================

Expõe um endpoint webhook (`/maestro/webhook`) que recebe eventos
assinados (HMAC-SHA256) do dispatcher do Maestro, vinculados a um
funcionário específico (`hr.employee`) via e-mail ou ID externo:

- risk.identified / risk.escalated
- approval.pending / approval.decided
- training.completed
- pulse_survey.due
- maturity.assessed

Os eventos aparecem como um botão inteligente "Maestro" no formulário do
funcionário, com histórico, nível de risco atual e linha do tempo (chatter
nativo do Odoo), como qualquer outro módulo de RH do sistema.

Também serve o app Maestro PWA (`/maestro/app`) com login por matrícula
(Badge ID) + PIN cadastrados no funcionário. O perfil/tela liberada é
determinado exclusivamente pelo cargo (hr.job > Perfil no app Maestro)
do funcionário autenticado — não há seleção manual de cargo no app.
""",
    'depends': ['hr', 'mail', 'hr_skills'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_maestro_event_views.xml',
        'views/hr_job_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_maestro_checklist_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
