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

_logger = logging.getLogger('ir_sequence')

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
        'code': openerp.osv.fields.selection(_code_get, 'Code', size=64, required=True),
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

    def create(self, cr, uid, values, context=None):
        values = self._add_missing_default_values(cr, uid, values, context)
        go = super(ir_sequence, self).create \
            if values['implementation'] == 'no_gap' else self.create_postgres
        return go(cr, uid, values, context)

    def create_postgres(self, cr, uid, values, context=None):
        """ Create a fast, gaps-allowed PostgreSQL sequence.

        :param values: same argument than for ``create()`` but the keys
            ``number_increment`` and ``number_next`` must be present.
            ``_add_missing_default_values()`` can be used to this effect.
        :return: id of the newly created record
        """
        id = super(ir_sequence, self).create(cr, uid, values, context)
        self._create_sequence(cr, id,
            values['number_increment'], values['number_next'])
        return id

    def unlink(self, cr, uid, ids, context=None):
        super(ir_sequence, self).unlink(cr, uid, ids, context)
        self._drop_sequence(cr, ids)
        return True

    def write(self, cr, uid, ids, values, context=None):
        ids = ids if isinstance(ids, (list, tuple)) else [ids]
        new_implementation = values.get('implementation')
        rows = self.read(cr, uid, ids, ['implementation',
            'number_increment', 'number_next'], context)
        super(ir_sequence, self).write(cr, uid, ids, values, context)
        
        for row in rows:
            # 4 cases: we test the previous impl. against the new one.
            if row['implementation'] == 'standard':
                i = values.get('number_increment', row['number_increment'])
                n = values.get('number_next', row['number_next'])
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

    def next_by_id(self, cr, uid, sequence_id, context=None):
        """ Draw an interpolated string using the specified sequence."""
        self.check_read(cr, uid)
        res = self._select_by_code_or_id(cr, uid, sequence_id,
            'id', False, context)
        return self._next(cr, uid, res, context)

    def next_by_code(self, cr, uid, sequence_code, context=None):
        """ Draw an interpolated string using the specified sequence."""
        self.check_read(cr, uid)
        res = self._select_by_code_or_id(cr, uid, sequence_code,
            'code', False, context)
        return self._next(cr, uid, res, context)

    def get_id(self, cr, uid, sequence_code_or_id, code_or_id='id', context=None):
        """ Draw an interpolated string using the specified sequence.

        The sequence to use is specified by the ``sequence_code_or_id``
        argument, which can be a code or an id (as controlled by the
        ``code_or_id`` argument. This method is deprecated.
        """
        _logger.warning("ir_sequence.get() and ir_sequence.get_id() are deprecated. "
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

    def _next(self, cr, uid, sequence, context=None):
        if not sequence:
            return False

        if sequence['implementation'] == 'standard':
            cr.execute("""
                SELECT nextval('ir_sequence_%03d')
                """ % sequence['id'])
            sequence['number_next'] = cr.fetchone()
        else:
            # Read again with FOR UPDATE NO WAIT.
            sequence = self._select_by_code_or_id(cr, uid, sequence['id'],
                'id', True, context)
            cr.execute("""
                UPDATE ir_sequence
                SET number_next=number_next+number_increment
                WHERE id=%s
                """, (sequence['id'],))

        d = self._interpolation_dict()
        interpolated_prefix = self._interpolate(sequence['prefix'], d)
        interpolated_suffix = self._interpolate(sequence['suffix'], d)
        if sequence['number_next']:
            return interpolated_prefix + '%%0%sd' % sequence['padding'] % \
                sequence['number_next'] + interpolated_suffix
        else:
            # TODO what is this case used for ?
            return interpolated_prefix + interpolated_suffix

    def _select_by_code_or_id(self, cr, uid, sequence_code_or_id, code_or_id,
            for_update_no_wait, context=None):
        """ Read a sequence object.

        There is no access rights check on the sequence itself.
        """
        assert code_or_id in ('code', 'id')
        res_company = self.pool.get('res.company')
        company_ids = res_company.search(cr, uid, [], context=context)
        funw = 'FOR UPDATE NOWAIT' if for_update_no_wait else ''
        cr.execute("""
            SELECT id, number_next, prefix, suffix, padding, implementation
            FROM ir_sequence
            WHERE %s=%%s
              AND active=true
              AND (company_id in %%s or company_id is NULL)
            %s
            """ % (code_or_id, funw),
            (sequence_code_or_id, tuple(company_ids)))
        return cr.dictfetchone()

    def _create_sequence(self, cr, id, number_increment, number_next):
        """ Create a PostreSQL sequence.

        There is no access rights check.
        """
        assert isinstance(id, (int, long))
        cr.execute("""
            CREATE SEQUENCE ir_sequence_%03d INCREMENT BY %%s START WITH %%s
            """ % id, (number_increment, number_next))

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
        cr.execute("""
            DROP SEQUENCE IF EXISTS %s RESTRICT
            """ % names)

    def _alter_sequence(self, cr, id, number_increment, number_next):
        """ Alter a PostreSQL sequence.

        There is no access rights check.
        """
        assert isinstance(id, (int, long))
        cr.execute("""
            ALTER SEQUENCE ir_sequence_%03d INCREMENT BY %%s RESTART WITH %%s
            """ % id, (number_increment, number_next))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
