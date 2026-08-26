{
    'name': 'Real Estate',       # Display name of your app
    'version': '1.0',            # Your module version
    'depends': ['base',
                'contacts'
                ],         # Required Odoo modules (always include 'base')
    'author': 'Mohammed Alsalmi',       # Your name/company
    'category': 'Real Estate',   # App category (e.g., Sales, HR)
    'description': "Module for managing real estate properties.first try using odoo",
    # 'sequence':'3',
    'data': [
         'security/ir.model.access.csv',
         'view/estate_property_views.xml',
         'view/estate_property_type_view.xml',
         'view/estate_property_tag_view.xml',
         'view/estate_property_offer_view.xml',
         'view/estate_menus.xml',
         'view/estate_res_users_view.xml',

    ],                  # List of XML/CSV data files (leave empty for now)
    'application': True,
    'installable': True
}