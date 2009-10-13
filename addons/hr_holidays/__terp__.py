# -*- coding: utf-8 -*-


{
    "name" : "Human Resources: Holidays management",
    "version" : "1.5",
    "author" : "Tiny & Axelor",
    "category" : "Generic Modules/Human Resources",
    "website" : "http://www.openerp.com",
    "description": """Human Ressources: Holidays tracking and workflow

    This module allows you to manage leaves and leaves requests.

    Note that:
    - A synchronisation with an internal agenda (use of the CRM module) is possible: in order to automatically create a case when an holiday request is accepted, you have to link the holidays status to a case section. You can set up this info and your colour preferences in
                HR \ Configuration \ Holidays Status
    - An employee can make an ask for more off-days by making a new Allocation It will increase his total of that leave type available (if the request is accepted).
    - There are two ways to print the employee's holidays:
        * The first will allow to choose employees by department and is used by clicking the menu item located in
                HR \ Holidays Request \ Print Summary of Holidays
        * The second will allow you to choose the holidays report for specific employees. Go on the list
                HR \ Employees \ Employees
            then select the ones you want to choose, click on the print icon and select the option
                'Print Summary of Employee's Holidays'
    - The wizard allows you to choose if you want to print either the Confirmed & Validated holidays or only the Validated ones. These states must be set up by a user from the group 'HR' and with the role 'holidays'. You can define these features in the security tab from the user data in
                Administration \ Users \ Users
            for example, you maybe will do it for the user 'admin'.
""",
    'author': 'Tiny & Axelor',
    'website': 'http://www.openerp.com',
    'depends': ['hr', 'crm_configuration', 'process'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'hr_workflow.xml',
        'hr_view.xml',
        'hr_holidays_report.xml',
        'hr_holidays_wizard.xml',
        #'process/hr_holidays_process.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0086579209325',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
