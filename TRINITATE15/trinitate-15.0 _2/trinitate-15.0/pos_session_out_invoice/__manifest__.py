# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "out invoice with cost 0",
    "summary": "Deleted out invoice with cost 0 and point of sale button for reconciliations",
    "version": "15.0.1.0.1",
    "category": "account",
    "author": "Jarsa",
    "website": "https://www.jarsa.com.mx",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "account_accountant",
    ],
    "data": [
        "views/pos_session_view.xml",
    ],
}
