{
    'name': "estate_property",
    'category': 'Real Estate/Brokerage',
    'depends': ['base'],

    # data files always loaded at installation
    'data': [
      'security/security.xml',
      'security/ir.model.access.csv',
      'view/estate_menus.xml',
      'view/viewstable.xml',
    ],
    # data files containing optionally loaded demonstration data
    'license': 'LGPL-3',
}