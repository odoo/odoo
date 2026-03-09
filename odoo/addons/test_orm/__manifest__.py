{
    'name': 'Test ORM',
    'category': 'Hidden/Tests',
    'description': """A module to test the ORM.""",
    'depends': ['base'],
    'data': [
        # 'data/test_access_rights_data.xml',
        # 'data/test_action_bindings.xml',
        # 'data/test_inherits.xml',
        # 'data/test_orm_data.xml',
        # 'data/test_translated_field/test_model_data.xml',
        # 'security/ir.model.access.csv',
        # 'security/test_access_rights_security.xml',
        # 'security/test_orm_security.xml',
        # 'views/test_orm_views.xml',

        # DATA
        'data/test_access_feedback_data.xml',
        'data/test_action_bindings.xml',
        'data/test_translated_field/test_model_data.xml',

        # SECURITY
        'security/test_access_feedback/ir.model.access.csv',
        'security/test_action_bindings/ir.model.access.csv',
        'security/test_autovacuum/ir.model.access.csv',
        'security/test_check_access/ir.model.access.csv',
        'security/test_check_access/test_check_access.xml',
        'security/test_company_checks/ir.model.access.csv',
        'security/test_convert/ir.model.access.csv',
        'security/test_convert_env/ir.model.access.csv',

        # VIEWS
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
