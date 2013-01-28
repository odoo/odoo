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

import logging
import time

import openerp
from openerp.osv import osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

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

def _code_get(self, cr, uid, context=None):
    cr.execute('select code, name from ir_sequence_type')
    return cr.fetchall()

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
        'code': openerp.osv.fields.selection(_code_get, 'Code', size=64),
        'implementation': openerp.osv.fields.selection( # TODO update the view
            [('standard', 'Standard'), ('no_gap', 'No gap')],
            'Implementation', required=True,
            help="Two sequence object implementations are offered: Standard "
            "and 'No gap'. The later is slower than the former but forbids any"
            " gap in the sequence (while they are possible in the former)."),
        'active': openerp.osv.fields.boolean('Active'),
        'prefix': openerp.osv.fields.char('Prefix', size=64, help="Prefix value of the record for the sequence"),
        'suffix': openerp.osv.fields.char('Suffix', size=64, help="Suffix value of the record for the sequence"),
        'number_next': openerp.osv.fields.integer('Next Number', required=True, help="Next number of this sequence"),
        'number_increment': openerp.osv.fields.integer('Increment Number', required=True, help="The next number of the sequence will be incremented by this number"),
        'padding' : openerp.osv.fields.integer('Number Padding', required=True, help="OpenERP will automatically adds some '0' on the left of the 'Next Number' to get the required padding size."),
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

    def init(self, cr):
        return # Don't do the following index yet.
        # CONSTRAINT/UNIQUE INDEX on (code, company_id) 
        # /!\ The unique constraint 'unique_name_company_id' is not sufficient, because SQL92
        # only support field names in constraint definitions, and we need a function here:
        # we need to special-case company_id to treat all NULL company_id as equal, otherwise
        # we would allow duplicate (code, NULL) ir_sequences.
        cr.execute("""
            SELECT indexname FROM pg_indexes WHERE indexname =
            'ir_sequence_unique_code_company_id_idx'""")
        if not cr.fetchone():
            cr.execute("""
                CREATE UNIQUE INDEX ir_sequence_unique_code_company_id_idx
                ON ir_sequence (code, (COALESCE(company_id,-1)))""")

    def _create_sequence(self, cr, id, number_increment, number_next):
        """ Create a PostreSQL sequence.

        There is no access rights check.
        """
        if number_increment == 0:
             raise osv.except_osv(_('Warning!'),_("Increment number must not be zero."))
        assert isinstance(id, (int, long))
        sql = "CREATE SEQUENCE ir_sequence_%03d INCREMENT BY %%s START WITH %%s" % id
        cr.execute(sql, (number_increment, number_next))

    def _drop_sequence(self, cr, ids):
        """ Drop the PostreSQL sequence if it exists.

        There is no access rights check.
        """

        ids = ids if isinstance(ids, (list, tuple)) else [ids]
        assert all(isinstance(i, (int, long)) for i in ids), \
            "Only ids in (int, long) allowed."
        names = ','.join('ir_sequence_%03d' % i for i in ids)

        # RESTRICT is the default; it prevents dropping the sequence if an
        # object depends on it.
        cr.execute("DROP SEQUENCE IF EXISTS %s RESTRICT " % names)

    def _alter_sequence(self, cr, id, number_increment, number_next):
        """ Alter a PostreSQL sequence.

        There is no access rights check.
        """
        if number_increment == 0:
             raise osv.except_osv(_('Warning!'),_("Increment number must not be zero."))
        assert isinstance(id, (int, long))
        cr.execute("""
            ALTER SEQUENCE ir_sequence_%03d INCREMENT BY %%s RESTART WITH %%s
            """ % id, (number_increment, number_next))

    def create(self, cr, uid, values, context=None):
        """ Create a sequence, in implementation == standard a fast gaps-allowed PostgreSQL sequence is used.
        """
        values = self._add_missing_default_values(cr, uid, values, context)
        values['id'] = super(ir_sequence, self).create(cr, uid, values, context)
        if values['implementation'] == 'standard':
            self._create_sequence(cr, values['id'], values['number_increment'], values['number_next'])
        return values['id']

    def unlink(self, cr, uid, ids, context=None):
        super(ir_sequence, self).unlink(cr, uid, ids, context)
        self._drop_sequence(cr, ids)
        return True

    def write(self, cr, uid, ids, values, context=None):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        new_implementation = values.get('implementation')
        rows = self.read(cr, uid, ids, ['implementation', 'number_increment', 'number_next'], context)
        super(ir_sequence, self).write(cr, uid, ids, values, context)

        for row in rows:
            # 4 cases: we test the previous impl. against the new one.
            i = values.get('number_increment', row['number_increment'])
            n = values.get('number_next', row['number_next'])
            if row['implementation'] == 'standard':
                if new_implementation in ('standard', None):
                    self._alter_sequence(cr, row['id'], i, n)
                else:
                    self._drop_sequence(cr, row['id'])
            else:
                if new_implementation in ('no_gap', None):
                    pass
                else:
                    self._create_sequence(cr, row['id'], i, n)

        return True

    def _interpolate(self, s, d):
        if s:
            return s % d
        return  ''

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

    def _next(self, cr, uid, seq_ids, context=None):
        if not seq_ids:
            return False
        if context is None:
            context = {}
        force_company = context.get('force_company')
        if not force_company:
            force_company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        sequences = self.read(cr, uid, seq_ids, ['company_id','implementation','number_next','prefix','suffix','padding'])
        preferred_sequences = [s for s in sequences if s['company_id'] and s['company_id'][0] == force_company ]
        seq = preferred_sequences[0] if preferred_sequences else sequences[0]
        if seq['implementation'] == 'standard':
            cr.execute("SELECT nextval('ir_sequence_%03d')" % seq['id'])
            seq['number_next'] = cr.fetchone()
        else:
            cr.execute("SELECT number_next FROM ir_sequence WHERE id=%s FOR UPDATE NOWAIT", (seq['id'],))
            cr.execute("UPDATE ir_sequence SET number_next=number_next+number_increment WHERE id=%s ", (seq['id'],))
        d = self._interpolation_dict()
        interpolated_prefix = self._interpolate(seq['prefix'], d)
        interpolated_suffix = self._interpolate(seq['suffix'], d)
        return interpolated_prefix + '%%0%sd' % seq['padding'] % seq['number_next'] + interpolated_suffix

    def next_by_id(self, cr, uid, sequence_id, context=None):
        """ Draw an interpolated string using the specified sequence."""
        self.check_access_rights(cr, uid, 'read')
        company_ids = self.pool.get('res.company').search(cr, uid, [], order='company_id', context=context) + [False]
        ids = self.search(cr, uid, ['&',('id','=', sequence_id),('company_id','in',company_ids)])
        return self._next(cr, uid, ids, context)

    def next_by_code(self, cr, uid, sequence_code, context=None):
        """ Draw an interpolated string using a sequence with the requested code.
            If several sequences with the correct code are available to the user
            (multi-company cases), the one from the user's current company will
            be used.

            :param dict context: context dictionary may contain a
                ``force_company`` key with the ID of the company to
                use instead of the user's current company for the
                sequence selection. A matching sequence for that
                specific company will get higher priority. 
        """
        self.check_access_rights(cr, uid, 'read')
        company_ids = self.pool.get('res.company').search(cr, uid, [], order='company_id', context=context) + [False]
        ids = self.search(cr, uid, ['&',('code','=', sequence_code),('company_id','in',company_ids)])
        return self._next(cr, uid, ids, context)

    def get_id(self, cr, uid, sequence_code_or_id, code_or_id='id', context=None):
        """ Draw an interpolated string using the specified sequence.

        The sequence to use is specified by the ``sequence_code_or_id``
        argument, which can be a code or an id (as controlled by the
        ``code_or_id`` argument. This method is deprecated.
        """
        # TODO: bump up to warning after 6.1 release
        _logger.debug("ir_sequence.get() and ir_sequence.get_id() are deprecated. "
            "Please use ir_sequence.next_by_code() or ir_sequence.next_by_id().")
        if code_or_id == 'id':
            return self.next_by_id(cr, uid, sequence_code_or_id, context)
        else:
            return self.next_by_code(cr, uid, sequence_code_or_id, context)

    def get(self, cr, uid, code, context=None):
        """ Draw an interpolated string using the specified sequence.

        The sequence to use is specified by its code. This method is
        deprecated.
        """
        return self.get_id(cr, uid, code, 'code', context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
