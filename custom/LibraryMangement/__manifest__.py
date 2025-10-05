{
    'name': 'Library Mangement',       # Display name of your app
    'version': '1.0',            # Your module version
    # 'depends': ['base',
    #             'contacts'
    #             ],         # Required Odoo modules (always include 'base')
    'author': 'Mohammed Alsalmi',       # Your name/company
    'category': 'Mangement',   # App category (e.g., Sales, HR)
    'description': "Module for manging the broww system that in the libraries",
    # 'sequence':'3',
    'data': [
        'security/ir.model.access.csv',
        'view/library_mangement_books_view.xml',
        'view/library_mangement_auther.xml',
        'view/library_mangement_customer.xml',
        'view/library_mangement_borrow.xml',
        'view/library_mangement_menu.xml',
    ],                  # List of XML/CSV data files (leave empty for now)
    'application': True,
    'installable': True
}