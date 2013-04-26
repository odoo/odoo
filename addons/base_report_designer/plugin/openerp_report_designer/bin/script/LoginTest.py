#########################################################################
#
#  Copyright (c) 2003-2004 Danny Brewer d29583@groovegarden.com
#  Copyright (C) 2004-2010 OpenERP SA (<http://openerp.com>).
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#  See:  http://www.gnu.org/licenses/lgpl.html
#
#############################################################################

if __name__<>"package":
    from ServerParameter import *
    from lib.gui import *

class LoginTest:
    def __init__(self):
        if not loginstatus:
            Change(None)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
