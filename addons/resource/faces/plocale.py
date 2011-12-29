############################################################################
#   Copyright (C) 2005 by Reithinger GmbH
#   mreithinger@web.de
#
#   This file is part of faces.
#                                                                         
#   faces is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   faces is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
############################################################################

import gettext
import os.path
import locale
import sys

def _get_translation():
    try:
        return gettext.translation("faces")
    except:
        try:
            if sys.frozen:
                path = os.path.dirname(sys.argv[0])
                path = os.path.join(path, "resources", "faces", "locale")
            else:
                path = os.path.split(__file__)[0]
                path = os.path.join(path, "locale")

            return gettext.translation("faces", path)
        except Exception, e:
            return None

def get_gettext():
    trans = _get_translation()
    if trans: return trans.ugettext
    return lambda msg: msg
        

def get_encoding():
    trans = _get_translation()
    if trans: return trans.charset()
    return locale.getpreferredencoding()
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
