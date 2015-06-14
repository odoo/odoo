# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2011
#        Pexego Sistemas Informáticos. (http://pexego.es)
#    Copyright (c) 2014 Serv. Tecnol. Avanzados (http://www.serviciosbaeza.com)
#                       Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Relationship refund - origin invoice",
    "version": "1.0",
    "author": "Spanish Localization Team,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-spain",
    "contributors": [
        'Pexego <www.pexego.es>',
        'Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>',
    ],
    "category": "Localisation/Accounting",
    "depends": [
        'account',
    ],
    "data": [
        'views/account_invoice_view.xml',
    ],
    "installable": True,
}
