# -*- coding: utf-8 -*-

# Author: Gustavo Valverde <gvalverde@iterativo.do> iterativo | Consultores
# Contributors: Edser Solis - iterativo

# Odoo 8.0 author: Eneldo Serrata <eneldo@marcos.do>
# (Marcos Organizador de Negocios SRL..)
# Odoo 7.0 author: Jose Ernesto Mendez <tecnologia@obsdr.com>
# (Open Business Solutions SRL.)

# Copyright (c) 2016 - Present | iterativo, SRL. - http://iterativo.do
# All rights reserved.

{
    'name': 'Dominican Republic - Accounting',
    'version': '2.0',
    'category': 'Localization',
    'description': """

Localization Module for Dominican Republic
===========================================

Catálogo de Cuentas e Impuestos para República Dominicana, Compatible para
**Internacionalización** con **NIIF** y alineado a las normas y regulaciones
de la Dirección General de Impuestos Internos (**DGII**).

**Este módulo consiste de:**

- Catálogo de Cuentas Estándar (alineado a DGII y NIIF)
- Catálogo de Impuestos con la mayoría de Impuestos Preconfigurados
        - ITBIS para compras y ventas
        - Retenciones de ITBIS
        - Retenciones de ISR
        - Grupos de Impuestos y Retenciones:
                - Telecomunicaiones
                - Proveedores de Materiales de Construcción
                - Personas Físicas Proveedoras de Servicios
        - Otros impuestos
- Secuencias Preconfiguradas para manejo de todos los NCF
        - Facturas con Valor Fiscal (para Ventas)
        - Facturas para Consumidores Finales
        - Notas de Débito y Crédito
        - Registro de Proveedores Informales
        - Registro de Ingreso Único
        - Registro de Gastos Menores
        - Gubernamentales
- Posiciones Fiscales para automatización de impuestos y retenciones
        - Cambios de Impuestos a Exenciones (Ej. Ventas al Estado)
        - Cambios de Impuestos a Retenciones (Ej. Compra Servicios al Exterior)
        - Entre otros

**Nota:**
Esta localización, aunque posee las secuencias para NCF, las mismas no pueden
ser utilizadas sin la instalación de módulos de terceros o desarrollo
adicional.

Estructura de Codificación del Catálogo de Cuentas:
===================================================

**Un dígito** representa la categoría/tipo de cuenta del del estado financiero.
**1** - Activo        **4** - Cuentas de Ingresos y Ganancias
**2** - Pasivo        **5** - Costos, Gastos y Pérdidas
**3** - Capital       **6** - Cuentas Liquidadoras de Resultados

**Dos dígitos** representan los rubros de agrupación:
11- Activo Corriente
21- Pasivo Corriente
31- Capital Contable

**Cuatro dígitos** se asignan a las cuentas de mayor: cuentas de primer orden
1101- Efectivo y Equivalentes de Efectivo
2101- Cuentas y Documentos por pagar
3101- Capital Social

**Seis dígitos** se asignan a las sub-cuentas: cuentas de segundo orden
110101 - Caja
210101 - Proveedores locales

**Ocho dígitos** son para las cuentas de tercer orden (las visualizadas
en Odoo):
1101- Efectivo y Equivalentes
110101- Caja
11010101 Caja General
    """,
    'author': 'Gustavo Valverde - iterativo | Consultores de Odoo',
    'website': 'http://iterativo.do',
    'depends': ['account',
                'base_iban'
                ],
    'data': [
        # Basic accounting data
        'data/l10n_do_chart_data.xml',
        'data/account_account_tag_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_data.xml',
        'data/account_data.xml',
        'data/account.tax.template.xml',
        # Country States
        'data/l10n_do_state_data.xml',
        # Adds fiscal position
        'data/fiscal_position_template.xml',
        # configuration wizard, views, reports...
        'data/account_chart_template_data.yml',
    ],
}
