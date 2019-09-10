# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

# Why doing some multi-thread instead of using OSE capabilities ?
# For progress bar.

#
# Add a transparant multi-thread layer to all report rendering layers
#

# TODO: method to stock on the disk
class render(object):
    """ Represents a report job being rendered.
    
    @param bin_datas a dictionary of name:<binary content> of images etc.
    @param path the path in which binary files can be discovered, useful
            for components (images) of the report. It can be:
               - a string, relative or absolute path to images
               - a list, containing strings of paths.
            If a string is absolute path, it will be opened as such, else
            it will be passed to tools.file_open() which also considers zip
            addons.

    Reporting classes must subclass this class and redefine the __init__ and
    _render methods (not the other methods).

    """
    def __init__(self, bin_datas=None, path='.'):
        self.done = False
        if bin_datas is None:
            self.bin_datas = {}
        else:
            self.bin_datas = bin_datas
        self.path = path
    
    def _render(self):
        return None

    def render(self):
        self.done = False
        self._result = self._render()
        self.done = True
        return True
    
    def is_done(self):
        return self.done

    def get(self):
        if self.is_done():
            return self._result
        else:
            return None


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

