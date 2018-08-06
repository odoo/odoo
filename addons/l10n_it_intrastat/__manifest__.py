
{
    'name': 'Account - Intrastat',
    'version': '11.0.1.0.1',
    'category': 'Account',
    'author': 'Openforce'
              ', Link IT srl',
    'website': 'http://linkgroup.it/',
    'license': 'Other proprietary',
    "depends": [
        'sale_management',
        'product',
        'stock',
        'stock_account',
        'report_intrastat'],
    "data": [
        'security/ir.model.access.csv',
        'views/intrastat.xml',
        'views/product.xml',
        'views/account.xml',
        'views/config.xml',
        'data/account.intrastat.transation.nature.csv',
        'data/account.intrastat.transport.csv',
        'data/account.intrastat.custom.csv',
        'data/report.intrastat.code.csv',
        ],
    "demo": [
        'demo/product_demo.xml'
        ],
    "installable": True
}
