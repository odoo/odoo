# -*- coding: utf-8 -*-
import unittest2

import test_orm
import test_ir_sequence
import test_xmlrpc

# Explicit declaration list of test sub-modules.
suite = [
    test_xmlrpc, # Creates a database
    test_ir_sequence, # Assume an existing database
    test_orm, # Assume an existing database
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
