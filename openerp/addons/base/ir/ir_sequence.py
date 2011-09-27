# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
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

import time

import openerp

class ir_sequence_type(openerp.osv.osv.osv):
    _name = 'ir.sequence.type'
    _order = 'name'
    _columns = {
        'name': openerp.osv.fields.char('Name', size=64, required=True),
        'code': openerp.osv.fields.char('Code', size=32, required=True),
    }

    _sql_constraints = [
        ('code_unique', 'unique(code)', '`code` must be unique.'),
    ]

def _code_get(self, cr, uid, context={}):
    cr.execute('select code, name from ir_sequence_type')
    return cr.fetchall()

IMPLEMENTATION_SELECTION = \
    [('standard', 'Standard'), ('no_gap', 'No gap')]

class ir_sequence(openerp.osv.osv.osv):
    """ Sequence model.

    The sequence model allows to define and use so-called sequence objects.
    Such objects are used to generate unique identifiers in a transaction-safe
    way.

    """
    _name = 'ir.sequence'
    _order = 'name'
    _columns = {
        'name': openerp.osv.fields.char('Name', size=64, required=True),
        'code': openerp.osv.fields.selection(_code_get, 'Code', size=64, required=True), # TODO should it be unique?
        'implementation': openerp.osv.fields.selection( # TODO update the view
            IMPLEMENTATION_SELECTION, 'Implementation', required=True,
            help="Two sequence object implementations are offered: Standard "
            "and 'No gap'. The later is slower than the former but forbids any"
            " gap in the sequence (while they are possible in the former)."),
        'active': openerp.osv.fields.boolean('Active'),
        'prefix': openerp.osv.fields.char('Prefix', size=64, help="Prefix value of the record for the sequence"),
        'suffix': openerp.osv.fields.char('Suffix', size=64, help="Suffix value of the record for the sequence"),
        'number_next': openerp.osv.fields.integer('Next Number', required=True, help="Next number of this sequence"),
        'number_increment': openerp.osv.fields.integer('Increment Number', required=True, help="The next number of the sequence will be incremented by this number"),
        'padding' : openerp.osv.fields.integer('Number padding', required=True, help="OpenERP will automatically adds some '0' on the left of the 'Next Number' to get the required padding size."),
        'company_id': openerp.osv.fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'implementation': 'standard',
        'active': True,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'ir.sequence', context=c),
        'number_increment': 1,
        'number_next': 1,
        'padding' : 0,
    }

    def create(self, cr, uid, values, context=None):
        values = self._add_missing_default_values(cr, uid, values, context)
        go = super(ir_sequence, self).create \
            if values['implementation'] == 'standard' else self.create_nogap
        return go(cr, uid, values, context)

    def _interpolate(self, s, d):
        return s % d if s else ''

    def _interpolation_dict(self):
        t = time.localtime() # Actually, the server is always in UTC.
        return {
            'year': time.strftime('%Y', t),
            'month': time.strftime('%m', t),
            'day': time.strftime('%d', t),
            'y': time.strftime('%y', t),
            'doy': time.strftime('%j', t),
            'woy': time.strftime('%W', t),
            'weekday': time.strftime('%w', t),
            'h24': time.strftime('%H', t),
            'h12': time.strftime('%I', t),
            'min': time.strftime('%M', t),
            'sec': time.strftime('%S', t),
        }

    # TODO rename 'test' to 'code_or_id' in account/sequence.
    def get_id(self, cr, uid, sequence_code_or_id, code_or_id='id', context=None):
        """ Draw an interpolated string using the specified sequence.

        The sequence to use is specified by the ``sequence_code_or_id``
        argument, which can be a code or an id (as controlled by the
        ``code_or_id`` argument.
        """
        assert code_or_id in ('code', 'id')
        company_ids = self.pool.get('res.company').search(cr, uid, [], context=context)
        cr.execute('''
            SELECT id, number_next, prefix, suffix, padding
            FROM ir_sequence
            WHERE %s=%%s
              AND active=true
              AND (company_id in %%s or company_id is NULL)
            ORDER BY company_id, id
            LIMIT 1
            FOR UPDATE NOWAIT''' % code_or_id,
            (sequence_code_or_id, tuple(company_ids)))
        res = cr.dictfetchone()
        if res:
            d = self._interpolation_dict()
            interpolated_prefix = self._interpolate(res['prefix'], d)
            interpolated_suffix = self._interpolate(res['suffix'], d)
            cr.execute('UPDATE ir_sequence SET number_next=number_next+number_increment WHERE id=%s', (res['id'],))
            if res['number_next']:
                return interpolated_prefix + '%%0%sd' % res['padding'] % res['number_next'] + interpolated_suffix
            else:
                # TODO what is this case used for ?
                return interpolated_prefix + interpolated_suffix
        return False

    def get(self, cr, uid, code, context=None):
        """ Draw an interpolated string using the specified sequence.

        The sequence to use is specified by its code.
        """
        return self.get_id(cr, uid, code, 'code', context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
