# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'LATAM Localization Base',
    'version': '1.0',
    'category': 'Localization',
    'sequence': 14,
    'author': 'Odoo, ADHOC SA',
    'summary': 'LATAM Identification Types',
    'description': """
Add a new model named "Identification Type" that extend the vat field functionality in the partner and let the user to identify (an eventually invoice) to contacts not only with their fiscal tax ID (VAT) but with other types of identifications like national document, passport, foreign ID, etc. With this module installed you will see now in the partner form view two fields:

* Identification Type
* Identification Number

This behavior is a common requirement for some latam countries like Argentina and Chile. If your localization has this requirements then you need to depend on this module and define in your localization module the identifications types that are used in your country. Generally these types of identifications are defined by the government authorities that regulate the fiscal operations. For example:

* AFIP in Argentina defines DNI, CUIT (vat for legal entities), CUIL (vat for natural person), and another 80 valid identification types.

Each identification holds this information:

* name: short name of the identification
* description: could be the same short name or a long name
* country_id: the country where this identification belongs
* is_vat: identify this record as the corresponding VAT for the specific country.
* sequence: let us to sort the identification types depending on the ones that are most used.
* active: we can activate/inactivate identifications to make it easier to our customers

In order to make this module compatible for multi-company environments where we have companies that does not need/support this requirement, we have added generic identification types and generic rules to manage the contact information and make it transparent for the user when only use the VAT as we formerly know.

Generic Identifications:

* VAT: The Fiscal Tax Identification or VAT number, by default will be selected as identification type so the user will only need to add the related vat number.
* Passport
* Foreign ID (Foreign National Document)

Rules when creating a new partner: We will only see the identification types that are meaningful, taking into account these rules:

* If the partner have not country address set: Will show the generic identification types plus the ones defined in the partner's related company country (If the partner has not specific company then will show the identification types related to the current user company)

* If the partner has country address : will show the generic identification types plus the ones defined for the country of the partner.

When creating a new company, will set to the related partner always the related country is_vat identification type.

All the defined identification types can be reviewed and activate/deactivate in "Contacts / Configuration / Identification Type" menu.

This module is compatible with base_vat module in order to be able to validate VAT numbers for each country that have or not have the possibility to manage multiple identification types.
""",
    'depends': [
        'contacts',
        'base_vat',
    ],
    'data': [
        'data/l10n_latam.identification.type.csv',
        'views/res_partner_view.xml',
        'views/l10n_latam_identification_type_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_set_default_identification_type',
}
