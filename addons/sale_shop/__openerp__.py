# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
{
    "name": "Sale Shop",
    "category": 'Sales Management',
    "summary": """
        Multi Shop for ODOO""",
    "description": """

====================
**Help and Support**
====================
.. |icon_features| image:: sale_shop/static/src/img/icon-features.png
.. |icon_support| image:: sale_shop/static/src/img/icon-support.png
.. |icon_help| image:: sale_shop/static/src/img/icon-help.png

|icon_help| `Help <https://webkul.com/ticket/open.php>`_ |icon_support| `Support <https://webkul.com/ticket/open.php>`_ |icon_features| `Request new Feature(s) <https://webkul.com/ticket/open.php>`_
    """,
    "sequence": 1,
    "author": "Webkul Software Pvt. Ltd.",
    "website": "http://www.webkul.com",
    "version": '1.0',
    "depends": ['base', 'sale'],
    "data": [
        'views/shop_view.xml',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    'images': ['static/description/Banner.png'],
}
