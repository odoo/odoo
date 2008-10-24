# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
#
# Plan comptable général pour la France, conforme au
# Règlement n° 99-03 du 29 avril 1999
# Version applicable au 1er janvier 2005.
# Règlement disponible sur http://comptabilite.erp-libre.info
# Mise en forme et paramétrage par http://sisalp.fr et http://nbconseil.net
#
{
    "name" : "France - Plan comptable Societe - 99-03",
    "version" : "1.1",
    "author" : "SISalp-NBconseil",
    "category" : "Localisation/Account Charts",
    "website": "http://erp-libre.info",
    "depends" : ["base", "account", "account_chart", 'base_vat'],
    "init_xml" : [],
    "update_xml" : ["types.xml", "plan-99-03_societe.xml", "taxes.xml","fr_wizard.xml"],
    "demo_xml" : [],
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

