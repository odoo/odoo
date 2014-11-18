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

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta
from openerp import _, api, fields, models
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)


class ir_sequence_type(models.Model):
    _name = 'ir.sequence.type'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(size=32, required=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', '`code` must be unique.'),
    ]


def _code_get(self):
    self.env.cr.execute('select code, name from ir_sequence_type')
    return self.env.cr.fetchall()


class ir_sequence(models.Model):
    """ Sequence model.

    The sequence model allows to define and use so-called sequence objects.
    Such objects are used to generate unique identifiers in a transaction-safe
    way.

    """
    _name = 'ir.sequence'
    _order = 'name'

    def _get_number_next_actual(self):
        '''Return number from ir_sequence row when no_gap implementation,
        and number from postgres sequence when standard implementation.'''
        res = {}
        for element in self:
            if element.implementation != 'standard':
                element.number_next_actual = element.number_next
            else:
                # get number from postgres sequence. Cannot use currval, because that might give an error when
                # not having used nextval before.
                query = "SELECT last_value, increment_by, is_called FROM ir_sequence_%03d" % element.id
                self.env.cr.execute(query)
                (last_value, increment_by, is_called) = self.env.cr.fetchone()
                if is_called:
                    element.number_next_actual = last_value + increment_by
                else:
                    element.number_next_actual = last_value

    def _set_number_next_actual(self):
        for record in self:
            record.write({'number_next': record.number_next_actual or 0})

    name = fields.Char(size=64, required=True)
    code = fields.Selection(_code_get, 'Sequence Type', size=64)
    implementation = fields.Selection(
        [('standard', 'Standard'), ('no_gap', 'No gap')],
        'Implementation', required=True, default='standard',
        help="Two sequence object implementations are offered: Standard "
        "and 'No gap'. The later is slower than the former but forbids any"
        " gap in the sequence (while they are possible in the former).")
    active = fields.Boolean(default=True)
    prefix = fields.Char(help="Prefix value of the record for the sequence")
    suffix = fields.Char(help="Suffix value of the record for the sequence")
    number_next = fields.Integer('Next Number', required=True, default=1, help="Next number of this sequence")
    number_next_actual = fields.Integer(compute='_get_number_next_actual', inverse='_set_number_next_actual',
                                        required=True, string='Next Number', default=1,
                                        help="Next number that will be used. This number can be incremented "
                                        "frequently so the displayed value might already be obsolete")
    number_increment = fields.Integer('Increment Number', required=True, default=1,
                                      help="The next number of the sequence will be incremented by this number")
    padding = fields.Integer('Number Padding', required=True, default=0,
                             help="Odoo will automatically adds some '0' on the left of the "
                             "'Next Number' to get the required padding size.")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda s: s.env['res.company']._company_default_get('ir.sequence'))
    use_date_range = fields.Boolean('Use subsequences per date_range')
    date_range_ids = fields.One2many('ir.sequence.date_range', 'sequence_main_id', 'Subsequences')

    def init(self, cr):
        return  # Don't do the following index yet.
        # CONSTRAINT/UNIQUE INDEX on (code, company_id)
        # /!\ The unique constraint 'unique_name_company_id' is not sufficient, because SQL92
        # only support field names in constraint definitions, and we need a function here:
        # we need to special-case company_id to treat all NULL company_id as equal, otherwise
        # we would allow duplicate (code, NULL) ir_sequences.
        self.env.cr.execute("""
            SELECT indexname FROM pg_indexes WHERE indexname =
            'ir_sequence_unique_code_company_id_idx'""")
        if not self.env.cr.fetchone():
            self.env.cr.execute("""
                CREATE UNIQUE INDEX ir_sequence_unique_code_company_id_idx
                ON ir_sequence (code, (COALESCE(company_id,-1)))""")

    def _create_sequence(self, number_increment, number_next, seq_date_id=False):
        """ Create a PostreSQL sequence.

        There is no access rights check.
        """
        if number_increment == 0:
            raise Warning(_('Increment number must not be zero.'))
        if seq_date_id:
            sql = "CREATE SEQUENCE ir_sequence_%03d_%03d INCREMENT BY %%s START WITH %%s" % (self.id, seq_date_id.id)
        else:
            sql = "CREATE SEQUENCE ir_sequence_%03d INCREMENT BY %%s START WITH %%s" % self.id
        self.env.cr.execute(sql, (number_increment, number_next))

    def _drop_sequence(self):
        """ Drop the PostreSQL sequence if it exists.

        There is no access rights check.
        """
        names = []
        for seq in self:
            for seq_date_id in seq.date_range_ids:
                names.append('ir_sequence_%03d_%03d' % (seq.id, seq_date_id))
            names.append('ir_sequence_%03d' % seq.id)
        names = ','.join(names)

        # RESTRICT is the default; it prevents dropping the sequence if an
        # object depends on it.
        self.env.cr.execute("DROP SEQUENCE IF EXISTS %s RESTRICT " % names)

    def _alter_sequence(self, number_increment=None, number_next=None, seq_date_id=False):
        """ Alter a PostreSQL sequence.

        There is no access rights check.
        """
        if number_increment == 0:
            raise Warning(_("Increment number must not be zero."))
        if seq_date_id:
            seq_name = 'ir_sequence_%03d_%03d' % (self.id, seq_date_id.id)
        else:
            seq_name = 'ir_sequence_%03d' % (self.id)
        self.env.cr.execute("SELECT relname FROM pg_class WHERE relkind = %s AND relname=%s", ('S', seq_name))
        if not self.env.cr.fetchone():
            # sequence is not created yet, we're inside create() so ignore it, will be set later
            return
        statement = "ALTER SEQUENCE %s" % (seq_name, )
        if number_increment is not None:
            statement += " INCREMENT BY %d" % (number_increment, )
        if number_next is not None:
            statement += " RESTART WITH %d" % (number_next, )
        self.env.cr.execute(statement)

    @api.model
    def create(self, values):
        """ Create a sequence, in implementation == standard a fast gaps-allowed PostgreSQL sequence is used.
        """
        values = self._add_missing_default_values(values)
        seq = super(ir_sequence, self).create(values)
        if values['implementation'] == 'standard':
            seq._create_sequence(values['number_increment'], values['number_next'])
        return seq

    @api.multi
    def unlink(self):
        self._drop_sequence()
        return super(ir_sequence, self).unlink()

    @api.multi
    def write(self, values):
        new_implementation = values.get('implementation')

        for seq in self:
            # 4 cases: we test the previous impl. against the new one.
            i = values.get('number_increment', seq.number_increment)
            n = values.get('number_next', seq.number_next)
            if seq.implementation == 'standard':
                if new_implementation in ('standard', None):
                    # Implementation has NOT changed.
                    # Only change sequence if really requested.
                    if seq.number_next != n:
                        seq._alter_sequence(number_next=n)
                    if seq.number_increment != i:
                        seq._alter_sequence(number_increment=i)
                        for seq_date_id in seq.date_range_ids:
                            seq._alter_sequence(number_increment=i, seq_date_id=seq_date_id)
                else:
                    seq._drop_sequence()
            else:
                if new_implementation in ('no_gap', None):
                    pass
                else:
                    seq._create_sequence(i, n)

        return super(ir_sequence, self).write(values)

    def _interpolate(self, s, d):
        if s:
            return s % d
        return ''

    def _interpolation_dict(self):
        t = time.localtime()  # Actually, the server is always in UTC.
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

    def _next_do(self, seq_date_id=False):
        cr = self.env.cr
        if self.implementation == 'standard':
            if seq_date_id:
                sql = "SELECT nextval('ir_sequence_%03d_%03d')" % (self.id, seq_date_id.id)
            else:
                sql = "SELECT nextval('ir_sequence_%03d')" % self.id
            cr.execute(sql)
            number_next = cr.fetchone()
        else:
            if seq_date_id:
                model_name = 'ir_sequence_date_range'
                model_obj = self.env['ir.sequence.date_range']
                id = seq_date_id
            else:
                model_name = 'ir_sequence'
                model_obj = self
                id = self
            number_next = id.number_next
            cr.execute("SELECT number_next FROM %s WHERE id=%s FOR UPDATE NOWAIT" % (model_name, id.id))
            cr.execute("UPDATE %s SET number_next=number_next+%s WHERE id=%s " % (model_name, self.number_increment, id.id))
            model_obj.invalidate_cache(['number_next'], [id.id])
        d = self._interpolation_dict()
        try:
            interpolated_prefix = self._interpolate(self.prefix, d)
            interpolated_suffix = self._interpolate(self.suffix, d)
        except ValueError:
            raise Warning(_('Invalid prefix or suffix for sequence \'%s\'') % (self.get('name')))
        return interpolated_prefix + '%%0%sd' % self.padding % number_next + interpolated_suffix

    def _create_date_range_seq(self, date):
        year = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y')
        date_from = '{}-01-01'.format(year)
        date_to = '{}-12-31'.format(year)
        for line in self.date_range_ids:
            if date < line.date_from < date_to:
                date_to = datetime.strptime(line.date_from, '%Y-%m-%d') + timedelta(days=-1)
                date_to = date_to.strftime('%Y-%m-%d')
            elif date_from < line.date_to < date:
                date_from = datetime.strptime(line.date_to, '%Y-%m-%d') + timedelta(days=1)
                date_from = date_from.strftime('%Y-%m-%d')
        seq_date_id = self.env['ir.sequence.date_range'].sudo().create({
            'date_from': date_from,
            'date_to': date_to,
            'sequence_main_id': self.id,
        })
        if self.implementation == 'standard':
            self._create_sequence(self.number_increment, 1, seq_date_id=seq_date_id)
        return seq_date_id

    def _next(self):
        """ Returns the next number in the preferred sequence in all the ones given in self.
        """
        if self.use_date_range:
            dt = self.env.context.get('date', fields.Date.today())
            seq_date_id = False
            for line in self.date_range_ids:
                if line.date_from <= dt <= line.date_to:
                    seq_date_id = line
                    break
            if not seq_date_id:
                seq_date_id = self._create_date_range_seq(dt)
            return self._next_do(seq_date_id=seq_date_id)
        else:
            return self._next_do()

    @api.multi
    def next_by_id(self):
        """ Draw an interpolated string using the specified sequence."""
        self.check_access_rights('read')
        return self._next()

    @api.model
    def next_by_code(self, sequence_code):
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
        self.check_access_rights('read')
        company_ids = self.env['res.company'].search([]).ids + [False]
        seq_ids = self.search(['&', ('code', '=', sequence_code), ('company_id', 'in', company_ids)])
        if not seq_ids:
            return False
        force_company = self.env.context.get('force_company')
        if not force_company:
            self.env.user.company_id
        preferred_sequences = [s for s in seq_ids if s.company_id and s.company_id == force_company]
        seq_id = preferred_sequences[0] if preferred_sequences else seq_ids[0]
        return seq_id._next()

    @api.model
    def get_id(self, sequence_code_or_id, code_or_id='id'):
        """ Draw an interpolated string using the specified sequence.

        The sequence to use is specified by the ``sequence_code_or_id``
        argument, which can be a code or an id (as controlled by the
        ``code_or_id`` argument. This method is deprecated.
        """
        _logger.warning("ir_sequence.get() and ir_sequence.get_id() are deprecated. "
                        "Please use ir_sequence.next_by_code() or ir_sequence.next_by_id().")
        if code_or_id == 'id':
            return self.browse(sequence_code_or_id).next_by_id()
        else:
            return self.next_by_code(sequence_code_or_id)

    @api.model
    def get(self, code):
        """ Draw an interpolated string using the specified sequence.

        The sequence to use is specified by its code. This method is
        deprecated.
        """
        return self.get_id(code, 'code')


class ir_sequence_date_range(models.Model):
    _name = 'ir.sequence.date_range'
    _rec_name = "sequence_main_id"

    def _get_number_next_actual(self):
        '''Return number from ir_sequence row when no_gap implementation,
        and number from postgres sequence when standard implementation.'''
        for element in self:
            if element.sequence_main_id.implementation != 'standard':
                element.number_next_actual = element.number_next
            else:
                # get number from postgres sequence. Cannot use currval, because that might give an error when
                # not having used nextval before.
                query = "SELECT last_value, increment_by, is_called FROM ir_sequence_%03d_%03d" % (element.sequence_main_id, element.id)
                self.env.cr.execute(query)
                (last_value, increment_by, is_called) = self.env.cr.fetchone()
                if is_called:
                    element.number_next_actual = last_value + increment_by
                else:
                    element.number_next_actual = last_value

    def _set_number_next_actual(self):
        for record in self:
            record.write({'number_next': record.number_next_actual or 0})

    date_from = fields.Date('From', required=True)
    date_to = fields.Date('To', required=True)
    sequence_main_id = fields.Many2one("ir.sequence", 'Main Sequence', required=True, ondelete='cascade')
    number_next = fields.Integer('Next Number', required=True, default=1, help="Next number of this sequence")
    number_next_actual = fields.Integer(compute='_get_number_next_actual', inverse='_set_number_next_actual',
                                        required=True, string='Next Number', default=1,
                                        help="Next number that will be used. This number can be incremented "
                                        "frequently so the displayed value might already be obsolete")

    @api.multi
    def write(self, values):
        res = super(ir_sequence_date_range, self).write(values)
        for seq_date_id in self:
            if seq_date_id.sequence_main_id.implementation == 'standard':
                if values.get('number_next'):
                    seq_date_id.sequence_main_id._alter_sequence(number_next=values.get('number_next'), seq_date_id=seq_date_id)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
