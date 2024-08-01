# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Three way fiscal positions',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Three way fiscal positions',
    'description': """
        Fiscal positions enhancement module which allows the user to configure three way fiscal positions
        This can be useful for companies having warehouse out of their fiscal country which export goods.

        Example:
            - Company is in Belgium - company_id.country_id
            - Warehouse is in France - country_id
            - Customer is in Germany - delivery_country_id

        In this case, the company will have to pay the VAT in France and the customer will have to pay the VAT in Germany.
        All this while allowing the product's taxes to remain Belgian taxes.
""",
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'views/fiscal_position.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
