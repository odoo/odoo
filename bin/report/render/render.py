# -*- encoding: utf-8 -*-
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

import threading

#
# TODO: method to stock on the disk
# Les class de reporting doivent surclasser cette classe
# Les seules methodes qui peuvent etre redefinies sont:
#     __init__
#     _render
#
class render(object):
    def __init__(self, bin_datas={}, path='.'):
        self.done = False
        self.bin_datas = bin_datas
        self.path = path
    
    def _render(self):
        return None

    def render(self):
        self.done = False
        result = self._render()
        self._result = result
        self.done = True
        return True
    
    def is_done(self):
        res = self.done
        return res

    def get(self):
        if self.is_done():
            return self._result
        else:
            return None

if __name__=='__main__':
    import time
    print 'Multi-thread code !'
    r = render()
    r.render()
    while not r.is_done():
        print 'not yet!'
        time.sleep(1)
    print 'done!'


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

