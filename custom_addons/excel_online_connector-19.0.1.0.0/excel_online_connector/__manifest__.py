{
    'name': 'Excel Online Connector',
    'version': '19.0.1.0.0',
    'author': 'Niyu Labs',
    'category': 'Connector',
    'description': """
       The Odoo Excel Online Connector is a powerful integration tool that seamlessly connects your Odoo ERP system with Microsoft Excel, enabling effortless data synchronization and real-time reporting. With this connector, users can pull data from Odoo directly into Excel spreadsheets, automate exports, and generate dynamic reports for accounting, sales, inventory, and more—all without manual data transfers or complex setups  """,
    'summary': """
            Odoo Excel Connector integrates your Odoo to Excel.""",
    'website': 'https://niyulabs.com',
    'support': "info@niyulabs.com",
    'price': 0,
    'currency': 'USD',
    'live_test_url': 'https://niyulabs.gitbook.io',
    'license': 'OPL-1',
    'depends': ['base', 'web'],
    'images': ['static/description/banner.gif',],
    'data': [
        # 1) Access rights first:
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/excel_export_task_views.xml',
        # 'data/excel_export_cron.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
