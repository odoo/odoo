{
    'name': 'Estate Invoice',
    'version': '1.0',
    'depends': ['estate',
                'account',],
    'author': 'Mohammed Shaikhan Alsalmi',
    'category': 'Mangement',
    'description': "Module for create invoices for the estate porperty when the sold",
    # 'sequence':'3',
    'data': [
        'security/ir.model.access.csv',
        'view/estate_account_main.xml',
        'view/estate_account_property_view.xml',
    ],                  # List of XML/CSV data files (leave empty for now)
    'application': True,
    'installable': True
}