{
    'name': 'Restriction on Product Creation',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summery': 'This application enforces restrictions on product creation, ensuring better control over product management and maintaining data consistency. , Product Creation Restriction, Controlled Product Management, Product Data Governance, Product Master Restriction, Inventory Data Control, Product Creation Rules, Product Management Tool, Restricted Product Entry, Inventory Validation System, Product Entry Approval, Product Database Restriction, Controlled Inventory Creation, Product Consistency Management, Inventory Data Integrity, Product Addition Restrictions, Inventory Control Application, Restricted Product Setup, Product Management Compliance, Inventory Data Validation Tool, Product Creation Policy Enforcement',
    'author': 'INKERP',
    'website': "http://www.INKERP.com",
    'depends': ['product'],
    'data': [
        'security/group.xml',
        'views/product_template_view.xml',
        'views/product_product_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
