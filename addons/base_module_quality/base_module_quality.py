# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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


class abstract_quality_check(object):
    '''
        This Class provide...
    '''

    #This float have to store the rating of the module.
    #Used to compute the final score (average of all scores).
    score = 0.0

    #This char have to store the result.
    #Used to display the result of the test.
    result = ""

    #This char have to store the result with more details.
    #Used to provide more details if necessary.
    result_details = ""

    #This bool defines if the test can be run only if the module is installed.
    #True => the module have to be installed.
    #False => the module can be uninstalled.
    bool_installed_only = True  

    def __init__(self):
        '''
        this method should initialize the var 
        '''
        raise 'Not Implemented'

    def run_test(self, module_path=""):
        '''
        this method should do the test and fill the score, result and result_details var
        '''
        raise 'Not Implemented'



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

