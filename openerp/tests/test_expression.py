import unittest2

import openerp

class test_domain_normalization(unittest2.TestCase):
    def test_normalize_domain(self):
        expression = openerp.osv.expression
        norm_domain = domain = ['&',(1,'=',1),('a','=','b')]
        assert norm_domain == expression.normalize(domain), "Normalized domains should be left untouched"
        domain = [('x','in',['y','z']),('a.v','=','e'),'|','|',('a','=','b'),'!',('c','>','d'),('e','!=','f'),('g','=','h')]
        norm_domain = ['&','&','&'] + domain
        assert norm_domain == expression.normalize(domain), "Non-normalized domains should be properly normalized"
