# -*- coding: utf-8 -*-

from odoo import models, fields, _

class m(models.TransientModel):
    """ A model to provide source strings. """
    _name = 'test.translation.import'

    name = fields.Char('1XBUO5PUYH2RYZSA1FTLRYS8SPCNU1UYXMEYMM25ASV7JC2KTJZQESZYRV9L8CGB',
                       size=32, help='Efgh')

    _('Ijkl')

    # With the name label above, this source string should be generated twice.
    _('1XBUO5PUYH2RYZSA1FTLRYS8SPCNU1UYXMEYMM25ASV7JC2KTJZQESZYRV9L8CGB')
