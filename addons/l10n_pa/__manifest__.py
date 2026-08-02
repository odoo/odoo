# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Panama - Accounting',
    'version': '19.0.1.0.0',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pa'],
    'description': """
Panamenian accounting chart and tax localization.

Plan contable panameño e impuestos de acuerdo a disposiciones vigentes:
- ITBMS (Ley 31 de 1998 y Ley 8 de 2010): tasas del 7% (general), 10%
  (bebidas alcohólicas y servicios hoteleros) y 15% (tabaco y derivados),
  además de exenciones (exportaciones, canasta básica, medicinas, servicios
  médicos y transporte).
- ISR (Código Fiscal, Art. 733): 25% para personas jurídicas.
- Retenciones: 12.5% sobre intereses y regalías al exterior (Código Fiscal,
  Art. 733), 10% definitivo sobre dividendos (Ley 52 de 2012) y retención del
  50% del ITBMS por parte de los agentes de retención o Grandes Compradores
  (Decreto Ejecutivo 173 de 2021 y Decreto Ejecutivo 84 de 2005).
- Registro Único de Contribuyentes (RUC) de la DGI con validación de formato
  para personas naturales (cédula) y jurídicas (inscripción en el Registro
  Público).

Con la Colaboración de
- AHMNET CORP http://www.ahmnet.com

    """,
    'author': 'Cubic ERP',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
