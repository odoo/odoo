{
    'name' : "tn_payroll",
    'author' : "adem kaboubi",
    'category' : "",
    'version' : "17.0.0.1.0",
    'depends': ['hr', 'hr_contract','payroll'],
'data': [
    'data/sequence.xml',
    'views/hr_employee_views.xml',
    'views/hr_contract_views.xml',
    'views/societe.xml',
    'security/ir.model.access.csv',
],
    'assets': {
        'web.assets_backend': [
            'tn_payroll/static/src/css/style.css',
            'tn_payroll/static/src/css/style1.css',

        ],
    },

    'application' :True,


}