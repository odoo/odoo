# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright Eezee-It
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
from openerp import models


class AccountCodaImport(models.TransientModel):
    _inherit = "account.coda.import"

    def coda_parsing(self, cr, uid, ids, context={}, batch=False,
                     codafile=None, codafilename=None):
        """
        Specify into context that's a coda_import (used during bank.statement
        creation)
        Args:
            cr: database cursor
            uid: int
            ids: list of int
            context: dict
            batch:
            codafile:
            codafilename:

        Returns: dict

        """
        context.update({
            'coda_import': True,
        })
        return super(AccountCodaImport, self).coda_parsing(
            cr, uid, ids, context=context, batch=batch, codafile=codafile,
            codafilename=codafilename)
