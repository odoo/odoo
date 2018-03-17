# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class HotelHousekeepingActivityType(models.Model):

    _name = 'hotel.housekeeping.activity.type'
    _description = 'Activity Type'

    name = fields.Char('Name', size=64, required=True)
    activity_id = fields.Many2one('hotel.housekeeping.activity.type',
                                  'Activity Type')

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.activity_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.activity_id
            return res
        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            category_names = name.split(' / ')
            parents = list(category_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args,
                                             operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('activity_id', 'in',
                                              categories.ids)], domain])
                else:
                    domain = expression.AND([[('activity_id', 'in',
                                               category_ids)], domain])
                for i in range(1, len(category_names)):
                    domain = [[('name', operator,
                                ' / '.join(category_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]),
                                     limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()


class HotelActivity(models.Model):

    _name = 'hotel.activity'
    _description = 'Housekeeping Activity'

    h_id = fields.Many2one('product.product', 'Product', required=True,
                           delegate=True, ondelete='cascade', index=True)
    categ_id = fields.Many2one('hotel.housekeeping.activity.type',
                               string='Category')


class HotelHousekeeping(models.Model):

    _name = "hotel.housekeeping"
    _description = "Booking"
    _rec_name = 'room_no'

    current_date = fields.Date("Today's Date", required=True,
                               index=True,
                               states={'done': [('readonly', True)]},
                               default=(lambda *a:
                                        time.strftime
                                        (DEFAULT_SERVER_DATE_FORMAT)))
    clean_type = fields.Selection([('daily', 'Daily'),
                                   ('checkin', 'Check-In'),
                                   ('checkout', 'Check-Out')],
                                  'Clean Type', required=True,
                                  states={'done': [('readonly', True)]},)
    room_no = fields.Many2one('hotel.room', 'Room No', required=True,
                              states={'done': [('readonly', True)]},
                              index=True)
    activity_lines = fields.One2many('hotel.housekeeping.activities',
                                     'a_list', 'Activities',
                                     states={'done': [('readonly', True)]},
                                     help='Detail of housekeeping activities',)
    inspector = fields.Many2one('res.users', 'Inspector', required=True,
                                index=True,
                                states={'done': [('readonly', True)]})
    inspect_date_time = fields.Datetime('Inspect Date Time', required=True,
                                        states={'done': [('readonly', True)]})
    quality = fields.Selection([('excellent', 'Excellent'), ('good', 'Good'),
                                ('average', 'Average'), ('bad', 'Bad'),
                                ('ok', 'Ok')], 'Quality',
                               states={'done': [('readonly', True)]},
                               help="Inspector inspect the room and mark \
                                as Excellent, Average, Bad, Good or Ok. ")
    state = fields.Selection([('inspect', 'Inspect'), ('dirty', 'Dirty'),
                              ('clean', 'Clean'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled')], 'State',
                             states={'done': [('readonly', True)]},
                             index=True, required=True, readonly=True,
                             default=lambda *a: 'inspect')

    @api.multi
    def action_set_to_dirty(self):
        """
        This method is used to change the state
        to dirty of the hotel housekeeping
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'dirty'
        for line in self:
            line.quality = False
            for activity_line in line.activity_lines:
                activity_line.write({'clean': False})
                activity_line.write({'dirty': True})
        return True

    @api.multi
    def room_cancel(self):
        """
        This method is used to change the state
        to cancel of the hotel housekeeping
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'cancel'
        self.quality = False
        return True

    @api.multi
    def room_done(self):
        """
        This method is used to change the state
        to done of the hotel housekeeping
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'done'
        if not self.quality:
            raise ValidationError(_('Please update quality of work!'))
        return True

    @api.multi
    def room_inspect(self):
        """
        This method is used to change the state
        to inspect of the hotel housekeeping
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'inspect'
        self.quality = False
        return True

    @api.multi
    def room_clean(self):
        """
        This method is used to change the state
        to clean of the hotel housekeeping
        ---------------------------------------
        @param self: object pointer
        """
        self.state = 'clean'
        for line in self:
            line.quality = False
            for activity_line in line.activity_lines:
                activity_line.write({'clean': True})
                activity_line.write({'dirty': False})
        return True


class HotelHousekeepingActivities(models.Model):

    _name = "hotel.housekeeping.activities"
    _description = "Housekeeping Activities "

    a_list = fields.Many2one('hotel.housekeeping', string='Booking')
    today_date = fields.Date('Today Date')
    activity_name = fields.Many2one('hotel.activity',
                                    string='Housekeeping Activity')
    housekeeper = fields.Many2one('res.users', string='Housekeeper',
                                  required=True)
    clean_start_time = fields.Datetime('Clean Start Time',
                                       required=True)
    clean_end_time = fields.Datetime('Clean End Time', required=True)
    dirty = fields.Boolean('Dirty',
                           help='Checked if the housekeeping activity'
                           'results as Dirty.')
    clean = fields.Boolean('Clean', help='Checked if the housekeeping'
                           'activity results as Clean.')

    @api.constrains('clean_start_time', 'clean_end_time')
    def check_clean_start_time(self):
        '''
        This method is used to validate the clean_start_time and
        clean_end_time.
        ---------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.clean_start_time >= self.clean_end_time:
            raise ValidationError(_('Start Date Should be \
            less than the End Date!'))

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(HotelHousekeepingActivities, self).default_get(fields)
        if self._context.get('room_id', False):
            res.update({'room_id': self._context['room_id']})
        if self._context.get('today_date', False):
            res.update({'today_date': self._context['today_date']})
        return res
