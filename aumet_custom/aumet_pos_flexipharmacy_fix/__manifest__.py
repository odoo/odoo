# -*- coding: utf-8 -*-
{
    'name': "Aumet FlexiPharmacy Customization",
    'summary': 'flexi pharmacy customization',
    'category': 'Point of Sale',
    'version': '',
    'license': "",
    'description': """
        -quantity decimal accuracy 3 digit.
    """,
    'depends': ['point_of_sale', 'flexipharmacy'],
    'data': [
        'views/pharmacy_assets.xml',
    ],

    'qweb': [
        'static/src/xml/Popups/EditListInput.xml',
        'static/src/xml/Popups/EditListPopup.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
}
