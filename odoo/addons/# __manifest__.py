# __manifest__.py
{
    'name': 'Hospital Management Custom Module',
    'version': '1.0',
    'category': 'Healthcare',
    'summary': 'Customizations for the Hospital Management System',
    'author': 'Your Name',
    'depends': ['hospital_management'],  # This ensures the module depends on your existing hospital management module
    'data': [
        # You can add your XML files here for views and menu items
        'views/hospital_custom_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
