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


class bilan(base_report.base_report):

    def __init__(self, cr, uid, name, context):
        super(bilan, self).__init__(cr, uid, name, context)

    def set_context(self, objects, data, ids):
        super(bilan, self).set_context(objects, data, ids)

        self._load('bilan', self.localcontext['data']['form'])
        self._set_variable(
            'at1a',
            self.localcontext['bavar1'] + self.localcontext['bavar2'] + self.localcontext['bavar3']
            + self.localcontext['bavar4'] + self.localcontext[
                'bavar5'] + self.localcontext['bavar6']
            + self.localcontext['bavar7'] + self.localcontext[
                'bavar8'] + self.localcontext['bavar9']
            + self.localcontext['bavar10'] + self.localcontext[
                'bavar11'] + self.localcontext['bavar12']
            + self.localcontext['bavar13'] + self.localcontext[
                'bavar14'] + self.localcontext['bavar15']
            + self.localcontext['bavar16'] + self.localcontext[
                'bavar17'] + self.localcontext['bavar18']
            + self.localcontext['bavar19'] + self.localcontext['bavar20']
        )
        self._set_variable(
            'at1b',
            self.localcontext['bavar2b'] + self.localcontext[
                'bavar3b'] + self.localcontext['bavar4b']
            + self.localcontext['bavar5b'] + self.localcontext[
                'bavar6b'] + self.localcontext['bavar7b']
            + self.localcontext['bavar9b'] + self.localcontext[
                'bavar10b'] + self.localcontext['bavar11b']
            + self.localcontext['bavar12b'] + self.localcontext[
                'bavar13b'] + self.localcontext['bavar15b']
            + self.localcontext['bavar16b'] + self.localcontext[
                'bavar17b'] + self.localcontext['bavar18b']
            + self.localcontext['bavar19b'] + self.localcontext['bavar20b']
        )
        self._set_variable(
            'at1',
            self.localcontext['at1a'] + self.localcontext['at1b']
        )
        self._set_variable(
            'at2a',
            self.localcontext['bavar21'] + self.localcontext[
                'bavar22'] + self.localcontext['bavar23']
            + self.localcontext['bavar24'] + self.localcontext[
                'bavar25'] + self.localcontext['bavar26']
            + self.localcontext['bavar27'] + self.localcontext[
                'bavar28'] + self.localcontext['bavar29']
            + self.localcontext['bavar30'] + self.localcontext[
                'bavar31'] + self.localcontext['bavar32']
            + self.localcontext['bavar33']
        )
        self._set_variable(
            'at2b',
            self.localcontext['bavar21b'] + self.localcontext[
                'bavar22b'] + self.localcontext['bavar23b']
            + self.localcontext['bavar24b'] + self.localcontext[
                'bavar26b'] + self.localcontext['bavar27b']
            + self.localcontext['bavar29b'] + self.localcontext['bavar30b']
        )
        self._set_variable(
            'at2',
            self.localcontext['at2a'] + self.localcontext['at2b']
        )
        self._set_variable(
            'actif',
            self.localcontext['at1'] + self.localcontext['at2'] + self.localcontext['bavar34']
            + self.localcontext['bavar35'] + self.localcontext['bavar36']
        )
        self._set_variable(
            'pt1',
            self.localcontext['bpvar1'] + self.localcontext['bpvar2'] + self.localcontext['bpvar3']
            + self.localcontext['bpvar4'] + self.localcontext[
                'bpvar5'] + self.localcontext['bpvar6']
            + self.localcontext['bpvar7'] + self.localcontext[
                'bpvar8'] + self.localcontext['bpvar9']
            + self.localcontext['bpvar10'] + self.localcontext[
                'bpvar11'] + self.localcontext['bpvar12']
        )
        self._set_variable(
            'pt2',
            self.localcontext['bpvar13'] + self.localcontext['bpvar14']
        )
        self._set_variable(
            'pt3',
            self.localcontext['bpvar15'] + self.localcontext[
                'bpvar16'] + self.localcontext['bpvar17']
            + self.localcontext['bpvar18'] + self.localcontext[
                'bpvar19'] + self.localcontext['bpvar20']
            + self.localcontext['bpvar21'] + self.localcontext[
                'bpvar22'] + self.localcontext['bpvar23']
            + self.localcontext['bpvar24'] + self.localcontext['bpvar25']
        )
        self._set_variable(
            'passif',
            self.localcontext['pt1'] + self.localcontext['pt2'] + self.localcontext['pt3']
            + self.localcontext['bpvar26']
        )


class wrapped_report_bilan(osv.AbstractModel):
    _name = 'report.l10n_fr.report_l10nfrbilan'
    _inherit = 'report.abstract_report'
    _template = 'l10n_fr.report_l10nfrbilan'
    _wrapped_report_class = bilan

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
