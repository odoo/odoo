# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2014 Domatix (http://www.domatix.com)
#                       Angel Moya <angel.moya@domatix.com>
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
__name__ = ("Cambia columnas name y description")


def migrate_tax_template(cr, version):

    cr.execute("""ALTER TABLE account_tax
                  RENAME COLUMN name to name_to_description_temp""")
    cr.execute("""ALTER TABLE account_tax
                  RENAME COLUMN description to name""")
    cr.execute("""ALTER TABLE account_tax
                  RENAME COLUMN name_to_description_temp to description""")


def migrate(cr, version):
    if not version:
        return
    migrate_tax_template(cr, version)
