# -*- coding: utf-8 -*-
#
#
# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
#

import base_report
from openerp.osv import osv


class cdr(base_report.base_report):
    def __init__(self, cr, uid, name, context):
        super(cdr, self).__init__(cr, uid, name, context)

    def set_context(self, objects, data, ids):
        super(cdr, self).set_context(objects, data, ids)

        self._load('cdr', self.localcontext['data']['form'])
        self._set_variable(
            'ct1',
            self.localcontext['cdrc1']+self.localcontext['cdrc2']+self.localcontext['cdrc3']+
            self.localcontext['cdrc4']+self.localcontext['cdrc5']+self.localcontext['cdrc6']+
            self.localcontext['cdrc7']+self.localcontext['cdrc8']+self.localcontext['cdrc9']+
            self.localcontext['cdrc10']+self.localcontext['cdrc11']+self.localcontext['cdrc12']+
            self.localcontext['cdrc13']+self.localcontext['cdrc14']+self.localcontext['cdrc15']
        )
        self._set_variable(
            'ct3',
            self.localcontext['cdrc17']+self.localcontext['cdrc18']+self.localcontext['cdrc19']+
            self.localcontext['cdrc20']
        )
        self._set_variable(
            'ct4',
            self.localcontext['cdrc21']+self.localcontext['cdrc22']+self.localcontext['cdrc23']
        )
        self._set_variable(
            'charges',
            self.localcontext['ct1']+self.localcontext['cdrc16']+self.localcontext['ct3']+
            self.localcontext['ct4']+self.localcontext['cdrc24']+self.localcontext['cdrc25']
        )
        self._set_variable(
            'pta',
            self.localcontext['cdrp1']+self.localcontext['cdrp2']
        )
        self._set_variable(
            'ptb',
            self.localcontext['cdrp3']+self.localcontext['cdrp4']+self.localcontext['cdrp5']+
            self.localcontext['cdrp6']+self.localcontext['cdrp7']
        )
        self._set_variable(
            'pt1',
            self.localcontext['pta']+self.localcontext['ptb']
        )
        self._set_variable(
            'pt3',
            self.localcontext['cdrp9']+self.localcontext['cdrp10']+self.localcontext['cdrp11']+
            self.localcontext['cdrp12']+self.localcontext['cdrp13']+self.localcontext['cdrp14']
        )
        self._set_variable(
            'pt4',
            self.localcontext['cdrp15']+self.localcontext['cdrp16']+self.localcontext['cdrp17']
        )
        self._set_variable(
            'produits',
            self.localcontext['pt1']+self.localcontext['cdrp8']+self.localcontext['pt3']+
            self.localcontext['pt4']
        )


class wrapped_report_resultat(osv.AbstractModel):
    _name = 'report.l10n_fr.report_l10nfrresultat'
    _inherit = 'report.abstract_report'
    _template = 'l10n_fr.report_l10nfrresultat'
    _wrapped_report_class = cdr

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
