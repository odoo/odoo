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
- Retenciones: 12.5% sobre intereses, regalías y comisiones por servicios al
  exterior (Código Fiscal, Art. 733); dividendos 10% definitivo (general),
  5% (rentas de fuente extranjera, exportaciones, rentas exentas o usuarios de
  zonas francas) y 20% (acciones al portador), según Ley 52 de 2012; y
  retención del 50% del ITBMS por parte de los agentes de retención o Grandes
  Compradores (Decreto Ejecutivo 173 de 2021 y Decreto Ejecutivo 84 de 2005).
- Registro Único de Contribuyentes (RUC) de la DGI con validación de formato
  para personas naturales (cédula) y jurídicas (inscripción en el Registro
  Público).
- Ley 526 de 2026 (sustancia económica para rentas pasivas de fuente
  extranjera de grupos multinacionales, vigente desde el ejercicio fiscal
  2027; 15% único definitivo si no se cumple la sustancia).
- Código postal oficial geolocalizado (sistema implementado el 7 de mayo de
  2026 por Correos Panamá/COTEL e INEC, plataforma codigospostalespanama.
  gob.pa; formato alfanumérico tipo AMAXG-FL434), con validación de formato
  en res.partner mediante el codec vendered de panama-postal (MIT).

Con la Colaboración de
- AHMNET CORP http://www.ahmnet.com

Actualización y Mejoras
- Alvaro Samudio https://github.com/alvarosamudio
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
