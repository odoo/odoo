# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Serv. Tecnol. Avanz. (<http://www.serviciosbaeza.com>)
#                       Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
#                       FactorLibre (<http://factorlibre.com>)
#                       Hugo santos <hugo.santos@factorlibre.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
__name__ = u"Renombrar impuestos, códigos de impuestos y posiciones fiscales"


def rename_fiscal_positions(cr):
    cr.execute("""
        UPDATE account_fiscal_position
        SET name='Régimen Extracomunitario / Canarias, Ceuta y Melilla'
        WHERE name='Régimen Extracomunitario'
        """)


def rename_tax_codes(cr):
    tax_code_mapping = [
        # IVA devengado. Base
        {'previous_code': '--',
         'previous_name': 'IVA devengado. Base imponible', 'code': 'IDBI'},
        {'previous_code': '--',
         'previous_name': 'IVA Devengado Base Imponible', 'code': 'IDBI'},
        {'previous_code': '[01]',
         'code': 'RGIDBI4'},
        {'previous_code': '[04]',
         'previous_name': 'Régimen general IVA devengado. Base imponible 10%',
         'code': 'RGIDBI10'},
        {'previous_code': '[04]',
         'previous_name': 'Régimen general IVA Devengado. Base Imponible 10%',
         'code': 'RGIDBI10'},
        {'previous_code': '[07]',
         'previous_name': 'Régimen general IVA devengado. Base imponible 21%',
         'code': 'RGIDBI21'},
        {'previous_code': '[07]',
         'previous_name': 'Régimen general IVA Devengado. Base Imponible 21%',
         'code': 'RGIDBI21'},
        # IVA devengado. Cuota
        {'previous_code': '[21]', 'code': 'ITDC'},
        {'previous_code': '[03]', 'code': 'RGIDC4'},
        {'previous_code': '[06]',
         'previous_name': 'Régimen general IVA devengado. Cuota 10%',
         'code': 'RGIDC10'},
        {'previous_code': '[06]',
         'previous_name': 'Régimen general IVA Devengado. Cuota 10%',
         'code': 'RGIDC10'},
        {'previous_code': '[09]',
         'previous_name': 'Régimen general IVA devengado. Cuota 21%',
         'code': 'RGIDC21'},
        {'previous_code': '[09]',
         'previous_name': 'Régimen general IVA Devengado. Cuota 21%',
         'code': 'RGIDC21'},
        # Adquisiciones intracomunitarias
        {'previous_code': '[19]', 'code': 'AIDBYSBI'},
        {'previous_code': '[20]', 'code': 'AIDBYSC'},
        # IVA deducible. Base Imponible
        {'previous_code': '--',
         'previous_name': 'IVA deducible. Base imponible', 'code': 'ISBI'},
        {'previous_code': '--',
         'previous_name': 'IVA Deducible Base Imponible', 'code': 'ISBI'},
        {'previous_code': '--',
         'previous_name': 'Base de compensaciones Régimen Especial A., G. y'
         ' P. 12%', 'code': 'CREAGYPBI12'},
        # Base operaciones interiores corrientes
        {'previous_code': '[22]', 'code': 'OICBI'},
        {'previous_code': '--',
         'previous_name': 'Base operaciones interiores corrientes (4%)',
         'code': 'OICBI4'},
        {'previous_code': '--',
         'previous_name': 'Base operaciones interiores corrientes (10%)',
         'code': 'OICBI10'},
        {'previous_code': '--',
         'previous_name': 'Base operaciones interiores corrientes (21%)',
         'code': 'OICBI21'},
        # Base operaciones interiores bienes de inversión
        {'previous_code': '[24]', 'code': 'OIBIBI'},
        {'previous_code': '--',
         'previous_name': 'Base operaciones interiores bienes inversión (4%)',
         'code': 'OIBIBI4'},
        {'previous_code': '--',
         'previous_name': 'Base operaciones interiores bienes inversión (10%)',
         'code': 'OIBIBI10'},
        {'previous_code': '--',
         'previous_name': 'Base operaciones interiores bienes inversión (21%)',
         'code': 'OIBIBI21'},
        # Base importaciones de bienes corrientes
        {'previous_code': '[26]', 'code': 'IBCBI'},
        {'previous_code': '--',
         'previous_name': 'Base importaciones bienes y servicios corrientes'
         ' (4%)', 'code': 'IBYSCBI4'},
        {'previous_code': '--',
         'previous_name': 'Base importaciones bienes y servicios corrientes'
         ' (10%)', 'code': 'IBYSCBI10'},
        {'previous_code': '--',
         'previous_name': 'Base importaciones bienes y servicios corrientes'
         ' (21%)', 'code': 'IBYSCBI21'},
        # Base importaciones de bienes de inversión
        {'previous_code': '[28]', 'code': 'IBIBI'},
        {'previous_code': '--',
         'previous_name': 'Base importaciones bienes inversión (4%)',
         'code': 'IBIBI4'},
        {'previous_code': '--',
         'previous_name': 'Base importaciones bienes inversión (10%)',
         'code': 'IBIBI10'},
        {'previous_code': '--',
         'previous_name': 'Base importaciones bienes inversión (21%)',
         'code': 'IBIBI21'},
        # Adquisiciones intracomunitarias de bienes corrientes
        {'previous_code': '[30]', 'code': 'AIBYSCBI'},
        {'previous_code': '--',
         'previous_name': 'Base adquisiciones intracomunitarias bienes y'
         ' serv. corr. (4%)', 'code': 'AIBYSCBI4'},
        {'previous_code': '--',
         'previous_name': 'Base adquisiciones intracomunitarias bienes y'
         ' serv. corr. (10%)', 'code': 'AIBYSCBI10'},
        {'previous_code': '--',
         'previous_name': 'Base adquisiciones intracomunitarias bienes y'
         ' serv. corr. (21%)', 'code': 'AIBYSCBI21'},
        # Adquisiciones intracomunitarias de bienes de inversión
        {'previous_code': '[32]', 'code': 'AIBIBI'},
        {'previous_code': '--',
         'previous_name': 'Base adquisiciones intracomunitarias bienes'
         ' inversión (4%)', 'code': 'AIBIBI4'},
        {'previous_code': '--',
         'previous_name': 'Base adquisiciones intracomunitarias bienes'
         ' inversión (10%)', 'code': 'AIBIBI10'},
        {'previous_code': '--',
         'previous_name': 'Base adquisiciones intracomunitarias bienes'
         ' inversión (21%)', 'code': 'AIBIBI21'},
        # Base recargo de equivalencia
        {'previous_code': '--',
         'previous_name': 'Recargo equivalencia ded. Base imponible 0.5%',
         'code': 'REDBI05'},
        {'previous_code': '--',
         'previous_name': 'Recargo equivalencia ded. Base imponible 1.4%',
         'code': 'REDBI014'},
        {'previous_code': '--',
         'previous_name': 'Recargo equivalencia ded. Base imponible 5.2%',
         'code': 'REDBI52'},
        # Iva deducible cuotas
        {'previous_code': '[37]', 'code': 'ITADC'},
        {'previous_code': '34', 'code': 'CREAGYP12'},
        # Cuotas operaciones interiores corrientes
        {'previous_code': '[23]', 'code': 'SOICC'},
        {'previous_code': '--',
         'previous_name': 'Cuotas soportadas operaciones interiores corrientes'
         ' (4%)', 'code': 'SOICC4'},
        {'previous_code': '--',
         'previous_name': 'Cuotas soportadas operaciones interiores corrientes'
         ' (10%)', 'code': 'SOICC10'},
        {'previous_code': '--',
         'previous_name': 'Cuotas soportadas operaciones interiores corrientes'
         ' (21%)', 'code': 'SOICC21'},
        # Cuotas operaciones interiores con bienes de inversión
        {'previous_code': '[25]', 'code': 'SOIBIC'},
        {'previous_code': '--',
         'previous_name': 'Cuotas soportadas operaciones interiores bienes'
         ' inversión (4%)', 'code': 'SOIBIC4'},
        {'previous_code': '--',
         'previous_name': 'Cuotas soportadas operaciones interiores bienes'
         ' inversión (10%)', 'code': 'SOIBIC10'},
        {'previous_code': '--',
         'previous_name': 'Cuotas soportadas operaciones interiores bienes'
         ' inversión (21%)', 'code': 'SOIBIC21'},
        # Cuotas devengadas en importaciones de bienes y serv. corr.
        {'previous_code': '[27]', 'code': 'DIBCC'},
        {'previous_code': '--',
         'previous_name': 'Cuotas devengadas importaciones bienes y serv.'
         ' corr. (4%)', 'code': 'DIBYSCC4'},
        {'previous_code': '--',
         'previous_name': 'Cuotas devengadas importaciones bienes y serv.'
         ' corr. (10%)', 'code': 'DIBYSCC10'},
        {'previous_code': '--',
         'previous_name': 'Cuotas devengadas importaciones bienes y serv.'
         ' corr. (21%)', 'code': 'DIBYSCC21'},
        # Cuotas devengadas en importaciones de bienes de inversión
        {'previous_code': '[29]', 'code': 'DIBIC'},
        {'previous_code': '--',
         'previous_name': 'Cuotas devengadas importaciones bienes inversión'
         ' (4%)', 'code': 'DIBIC4'},
        {'previous_code': '--',
         'previous_name': 'Cuotas devengadas importaciones bienes inversión'
         ' (10%)', 'code': 'DIBIC10'},
        {'previous_code': '--',
         'previous_name': 'Cuotas devengadas importaciones bienes inversión'
         ' (21%)', 'code': 'DIBIC21'},
        # Adquisiciones intracomunitarias de bienes corrientes - Cuota
        {'previous_code': '[31]', 'code': 'AIBYSCC'},
        {'previous_code': '--',
         'previous_name': 'En adquisiciones intracomunitarias bienes y serv.'
         ' corr. (4%)', 'code': 'AIBYSCC4'},
        {'previous_code': '--',
         'previous_name': 'En adquisiciones intracomunitarias bienes y serv.'
         ' corr. (10%)', 'code': 'AIBYSCC10'},
        {'previous_code': '--',
         'previous_name': 'En adquisiciones intracomunitarias bienes y serv.'
         ' corr. (21%)', 'code': 'AIBYSCC21'},
        # Adquisiciones intracomunitarias bienes de inversión - Cuota
        {'previous_code': '[33]', 'code': 'AIBIC'},
        {'previous_code': '--',
         'previous_name': 'En adquisiciones intracomunitarias bienes inversión'
         ' (4%)', 'code': 'AIBIC4'},
        {'previous_code': '--',
         'previous_name': 'En adquisiciones intracomunitarias bienes inversión'
         ' (10%)', 'code': 'AIBIC10'},
        {'previous_code': '--',
         'previous_name': 'En adquisiciones intracomunitarias bienes inversión'
         ' (21%)', 'code': 'AIBIC21'},
        # Otros códigos de impuestos
        {'previous_code': '[42]', 'code': 'EIDBYS'},
        {'previous_code': '[43]', 'code': 'EYOA'},
        # Recargo equivalencia Cuota
        {'previous_code': '[12]',
         'previous_name': 'Recargo equivalencia. Cuota 0.5%',
         'code': 'REC05'},
        {'previous_code': '[15]',
         'previous_name': 'Recargo equivalencia. Cuota 1.4%',
         'code': 'REC014'},
        {'previous_code': '[18]',
         'previous_name': 'Recargo equivalencia. Cuota 5.2%',
         'code': 'REC52'},
        # Recargo equivalencia ded. Cuota
        {'previous_code': '[12]',
         'previous_name': 'Recargo equivalencia ded. Cuota 0.5%',
         'code': 'REDC05'},
        {'previous_code': '[15]',
         'previous_name': 'Recargo equivalencia ded. Cuota 1.4%',
         'code': 'REDC014'},
        {'previous_code': '[18]',
         'previous_name': 'Recargo equivalencia ded. Cuota 5.2%',
         'code': 'REDC52'},
        # Recargo equivalencia base imponible
        {'previous_code': '[10]', 'code': 'REBI05'},
        {'previous_code': '[13]', 'code': 'REBI014'},
        {'previous_code': '[16]', 'code': 'REBI52'},
        # IRPF Retenciones a cuenta
        {'previous_code': 'B.IRPF AC', 'code': 'IRACBI'},
        {'previous_code': 'B.IRPF1 AC', 'code': 'IRACBI1'},
        {'previous_code': 'B.IRPF2 AC', 'code': 'IRACBI2'},
        {'previous_code': 'B.IRPF7 AC', 'code': 'IRACBI7'},
        {'previous_code': 'B.IRPF9 AC', 'code': 'IRACBI9'},
        {'previous_code': 'B.IRPF15 AC', 'code': 'IRACBI15'},
        {'previous_code': 'B.IRPF20 AC', 'code': 'IRACBI20'},
        {'previous_code': 'B.IRPF21 AC', 'code': 'IRACBI21'},
        # IRPF total retenciones a cuenta
        {'previous_code': 'IRPF AC', 'code': 'ITRACC'},
        {'previous_code': 'IRPF1 AC', 'code': 'IRACC1'},
        {'previous_code': 'IRPF2 AC', 'code': 'IRACC2'},
        {'previous_code': 'IRPF7 AC', 'code': 'IRACC7'},
        {'previous_code': 'IRPF9 AC', 'code': 'IRACC9'},
        {'previous_code': 'IRPF15 AC', 'code': 'IRACC15'},
        {'previous_code': 'IRPF20 AC', 'code': 'IRACC20'},
        {'previous_code': 'IRPF21 AC', 'code': 'IRACC21'},
        # IRPF retenciones practicadas. base imponible
        {'previous_code': 'B.IRPF', 'code': 'IRPBI'},
        {'previous_code': 'B.IRPF1', 'code': 'IRPBI1'},
        {'previous_code': 'B.IRPF2', 'code': 'IRPBI2'},
        {'previous_code': 'B.IRPF7', 'code': 'IRPBI7'},
        {'previous_code': 'B.IRPF9', 'code': 'IRPBI9'},
        {'previous_code': 'B.IRPF15', 'code': 'IRPBI15'},
        {'previous_code': 'B.IRPF20', 'code': 'IRPBI20'},
        {'previous_code': 'B.IRPF21', 'code': 'IRPBI21'},
        # IRPF retenciones practicadas. total cuota
        {'previous_code': 'IRPF', 'code': 'ITRPC'},
        {'previous_code': 'IRPF1', 'code': 'IRPC1'},
        {'previous_code': 'IRPF2', 'code': 'IRPC2'},
        {'previous_code': 'IRPF7', 'code': 'IRPC7'},
        {'previous_code': 'IRPF9', 'code': 'IRPC9'},
        {'previous_code': 'IRPF15', 'code': 'IRPC15'},
        {'previous_code': 'IRPF20', 'code': 'IRPC20'},
        {'previous_code': 'IRPF21', 'code': 'IRPC21'},
        # IVA exento
        {'previous_code': '--',
         'previous_name': 'Base adquisiciones exentas',
         'code': 'AEBI'},
        {'previous_code': '--',
         'previous_name': 'Base ventas exentas',
         'code': 'OESDAD'},
    ]
    for mapping in tax_code_mapping:
        sql = """
        UPDATE account_tax_code
        SET code=%s
        WHERE code=%s"""
        if mapping.get('previous_name'):
            sql += " AND name=%s"
            cr.execute(sql, (mapping['code'], mapping['previous_code'],
                             mapping['previous_name']))
        else:
            cr.execute(sql, (mapping['code'], mapping['previous_code']))


def rename_taxes(cr):
    tax_mapping = {
        'S_IVA4': 'S_IVA4B',
        'S_IVA10': 'S_IVA10B',
        'S_IVA21': 'S_IVA21B',
        'P_IVA21_IC_SV': 'P_IVA21_SP_IN',
        'P_IVA21_IC_SV_1': 'P_IVA21_SP_IN_1',
        'P_IVA21_IC_SV_2': 'P_IVA21_SP_IN_2',
    }
    for old_description, new_description in tax_mapping.iteritems():
        sql = """
        UPDATE account_tax
        SET description=%s
        WHERE description=%s"""
        cr.execute(sql, (new_description, old_description))


def change_refunds_tax_codes(cr):
    """Cambia los códigos de impuestos de los abonos posteriores a 2014 para
    que vayan a la parte de modificación de bases/cuotas en lugar de minorar
    las bases/cuotas normales.
    """
    refund_tax_codes = {
        # IVA repercutido
        'RGIDBI4': 'MBYCRBI',
        'RGIDBI10': 'MBYCRBI',
        'RGIDBI21': 'MBYCRBI',
        'RGIDC4': 'MBYCRC',
        'RGIDC10': 'MBYCRC',
        'RGIDC21': 'MBYCRC',
        # Recargo equivalencia compras
        'REDBI05': 'RDDSBI',
        'REDBI014': 'RDDSBI',
        'REDBI52': 'RDDSBI',
        'REDC05': 'RDDSC',
        'REDC014': 'RDDSC',
        'REDC52': 'RDDSC',
        # Recargo equivalencia ventas
        'REBI05': 'MBYCDRDERBI',
        'REBI014': 'MBYCDRDERBI',
        'REBI52': 'MBYCDRDERBI',
        'REC05': 'MBYCDRDERC',
        'REC014': 'MBYCDRDERC',
        'REC52': 'MBYCDRDERC',
        # IVA soportado
        'OICBI4': 'RDDSBI',
        'OIBIBI4': 'RDDSBI',
        'OICBI10': 'RDDSBI',
        'OIBIBI10': 'RDDSBI',
        'OICBI21': 'RDDSBI',
        'OIBIBI21': 'RDDSBI',
        'SOICC4': 'RDDSC',
        'SOIBIC4': 'RDDSC',
        'SOICC10': 'RDDSC',
        'SOIBIC10': 'RDDSC',
        'SOICC21': 'RDDSC',
        'SOIBIC21': 'RDDSC',
        # Importaciones
        'IBYSCBI4': 'RDDSBI',
        'IBYSCBI10': 'RDDSBI',
        'IBYSCBI21': 'RDDSBI',
        'IBIBI4': 'RDDSBI',
        'IBIBI10': 'RDDSBI',
        'IBIBI21': 'RDDSBI',
        'DIBYSCC4': 'RDDSC',
        'DIBYSCC10': 'RDDSC',
        'DIBYSCC21': 'RDDSC',
        'DIBIC4': 'RDDSC',
        'DIBIC10': 'RDDSC',
        'DIBIC21': 'RDDSC',
        # Intracomunitario
        'AIBYSCBI4': 'RDDSBI',
        'AIBYSCBI10': 'RDDSBI',
        'AIBYSCBI21': 'RDDSBI',
        'AISCBI4': 'RDDSBI',
        'AISCBI10': 'RDDSBI',
        'AISCBI21': 'RDDSBI',
        'AIBIBI4': 'RDDSBI',
        'AIBIBI10': 'RDDSBI',
        'AIBIBI21': 'RDDSBI',
        'AIBYSCC4': 'RDDSC',
        'AIBYSCC10': 'RDDSC',
        'AIBYSCC21': 'RDDSC',
        'AISCC4': 'RDDSC',
        'AISCC10': 'RDDSC',
        'AISCC21': 'RDDSC',
        'AIBIC4': 'RDDSC',
        'AIBIC10': 'RDDSC',
        'AIBIC21': 'RDDSC',
        'AIDBYSBI': 'MBYCRBI',
        'AIBBI': 'MBYCRBI',
        'AIBIBIA': 'MBYCRBI',
        'OCIDSPEAIBI': 'MBYCRBI',
        'AISBI': 'MBYCRBI',
        'AIDBYSC': 'MBYCRC',
        'AIBC': 'MBYCRC',
        'AIBICA': 'MBYCRC',
        'OOCIDSPEAIC': 'MBYCRC',
        'AISC': 'MBYCRC',
    }
    cr.execute("SELECT id FROM res_company")
    for record in cr.fetchall():
        company_id = record[0]
        for old_tax_code, new_tax_code in refund_tax_codes.iteritems():
            cr.execute(
                "SELECT id FROM account_tax_code WHERE code=%s",
                (new_tax_code, ))
            new_tax_code_id = cr.fetchone()
            if not new_tax_code_id:
                # Create fake tax code
                cr.execute(
                    """
                    INSERT INTO account_tax_code
                    (code, name, sign, company_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """, (new_tax_code, new_tax_code, 1.0, company_id))
                new_tax_code_id = cr.fetchone()[0]
            cr.execute(
                """
                UPDATE account_move_line aml
                SET tax_code_id=%s
                FROM account_tax_code atc
                WHERE aml.tax_code_id=atc.id
                  AND atc.code=%s
                  AND aml.tax_amount < 0
                  AND aml.date>='2014-01-01'
                  AND aml.company_id=%s
                """, (new_tax_code_id, old_tax_code, company_id))


def migrate(cr, version):
    if not version:
        return
    rename_fiscal_positions(cr)
    rename_tax_codes(cr)
    rename_taxes(cr)
    change_refunds_tax_codes(cr)
