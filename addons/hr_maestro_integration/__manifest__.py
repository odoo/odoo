# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Maestro Integration (NR-1 / Psychosocial Risk)',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Recebe eventos da plataforma Maestro Intelligence (webhooks) e registra risco psicossocial no funcionário',
    'description': """
Integração com a plataforma Maestro Intelligence
==================================================

Expõe um endpoint webhook (`/maestro/webhook`) que recebe eventos
assinados (HMAC-SHA256) do dispatcher do Maestro:

- risk.identified / risk.escalated
- approval.pending / approval.decided
- training.completed
- pulse_survey.due
- maturity.assessed

Os eventos são vinculados ao funcionário (`hr.employee`) pelo e-mail e
registrados como histórico de risco psicossocial / treinamento, visível
diretamente no formulário do funcionário.
""",
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_maestro_event_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
