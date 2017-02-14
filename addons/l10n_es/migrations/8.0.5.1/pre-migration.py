# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Serv. Tecnol. Avanz. (<http://www.serviciosbaeza.com>)
#                       Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
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
__name__ = u"Renombrar impuestos y posiciones fiscales"


def rename_fiscal_positions(cr):
    fp_mapping = {
        'Retención IRPF 19% Arrendamientos': 'Retención 19% arrendamientos',
        'Retención IRPF 20% Arrendamientos': 'Retención 20% arrendamientos',
        'Retención IRPF 21% Arrendamientos': 'Retención 21% arrendamientos',
    }
    for fp_old, fp_new in fp_mapping.iteritems():
        cr.execute(
            """
            UPDATE account_fiscal_position
            SET name=%s
            WHERE name=%s
            """, (fp_new, fp_old))


def rename_taxes(cr):
    tax_mapping = {
        'S_IRPF19A': 'S_RAC19A',
        'S_IRPF20A': 'S_RAC20A',
        'S_IRPF21A': 'S_RAC21A',
        'P_IRPF19A': 'P_RAC19A',
        'P_IRPF20A': 'P_RAC20A',
        'P_IRPF21A': 'P_RAC21A',
    }
    for tax_old, tax_new in tax_mapping.iteritems():
        cr.execute(
            """
            UPDATE account_tax
            SET description=%s
            WHERE description=%s""", (tax_new, tax_old))


def migrate(cr, version):
    if not version:
        return
    rename_fiscal_positions(cr)
    rename_taxes(cr)
