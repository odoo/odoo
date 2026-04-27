# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp - Employee Referral',
    'version': '1.0',
    'category': 'Human Resources/Referrals',
    'sequence': 236,
    'summary': 'Let your employees share job positions and refer their friends by WhatsApp',
    'description': """Let your employees share job positions and refer their friends by WhatsApp""",
    'website': ' ',
    'depends': ['hr_referral', 'whatsapp'],
    'data': [
        'views/hr_job_views.xml',
        'data/whatsapp_template_data.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
