#@+leo-ver=4
#@+node:@file observer.py
#@@language python
#@<< Copyright >>
#@+node:<< Copyright >>
############################################################################
#   Copyright (C) 2005, 2006, 2007, 2008 by Reithinger GmbH
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
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
############################################################################

#@-node:<< Copyright >>
#@nl
"""
This module contains the base class for all observer objects
"""
#@<< Imports >>
#@+node:<< Imports >>
#@-node:<< Imports >>
#@nl
_is_source_ = True
#@+others
#@+node:class Observer
class Observer(object):
    """
    Base Class for all charts and reports.

    @var visible: Specifies if the observer is visible
           at the navigation bar inside the gui.

    @var link_view: syncronizes the marked objects in all views.

    """
    #@	<< declarations >>
    #@+node:<< declarations >>
    __type_name__ = None
    __type_image__ = None
    visible = True
    link_view = True

    __attrib_completions__ = { "visible" : 'visible = False',
                               "link_view" : "link_view = False" }


    #@-node:<< declarations >>
    #@nl

    #@    @+others
    #@+node:register_editors
    def register_editors(cls, registry):
        pass

    register_editors = classmethod(register_editors)

    #@-node:register_editors
    #@-others

#@-node:class Observer
#@-others
factories = { }
clear_cache_funcs = {}
#@-node:@file observer.py
#@-leo

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
