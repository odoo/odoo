# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
from odoo.exceptions import ValidationError, UserError
import pytz


class HotelFolio(models.Model):

    _inherit = 'hotel.folio'
    _order = 'reservation_id desc'

    reservation_id = fields.Many2one('hotel.reservation',
                                     string='Booking Id')

    @api.multi
    def write(self, vals):
        context = dict(self._context)
        if not context:
            context = {}
        context.update({'from_reservation': True})
        res = super(HotelFolio, self).write(vals)
        reservation_line_obj = self.env['hotel.room.reservation.line']
        for folio_obj in self:
            if folio_obj.reservation_id:
                for reservation in folio_obj.reservation_id:
                    reservation_obj = (reservation_line_obj.search
                                       ([('reservation_id', '=',
                                          reservation.id)]))
                    if len(reservation_obj) == 1:
                        for line_id in reservation.reservation_line:
                            line_id = line_id.reserve
                            for room_id in line_id:
                                vals = {'room_id': room_id.id,
                                        'check_in': folio_obj.checkin_date,
                                        'check_out': folio_obj.checkout_date,
                                        'state': 'assigned',
                                        'reservation_id': reservation.id,
                                        }
                                reservation_obj.write(vals)
        return res


class HotelFolioLineExt(models.Model):

    _inherit = 'hotel.folio.line'

    @api.onchange('checkin_date', 'checkout_date')
    def on_change_checkout(self):
        res = super(HotelFolioLineExt, self).on_change_checkout()
        hotel_room_obj = self.env['hotel.room']
        avail_prod_ids = []
        hotel_room_ids = hotel_room_obj.search([])
        for room in hotel_room_ids:
            assigned = False
            for line in room.room_reservation_line_ids:
                if line.status != 'cancel':
                    if(self.checkin_date <= line.check_in <=
                        self.checkout_date) or (self.checkin_date <=
                                                line.check_out <=
                                                self.checkout_date):
                        assigned = True
                    elif(line.check_in <= self.checkin_date <=
                         line.check_out) or (line.check_in <=
                                             self.checkout_date <=
                                             line.check_out):
                        assigned = True
            if not assigned:
                avail_prod_ids.append(room.product_id.id)
        return res

    @api.multi
    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        Update Hotel Room Booking line history"""
        reservation_line_obj = self.env['hotel.room.reservation.line']
        room_obj = self.env['hotel.room']
        prod_id = vals.get('product_id') or self.product_id.id
        chkin = vals.get('checkin_date') or self.checkin_date
        chkout = vals.get('checkout_date') or self.checkout_date
        is_reserved = self.is_reserved
        if prod_id and is_reserved:
            prod_domain = [('product_id', '=', prod_id)]
            prod_room = room_obj.search(prod_domain, limit=1)
            if (self.product_id and self.checkin_date and self.checkout_date):
                old_prd_domain = [('product_id', '=', self.product_id.id)]
                old_prod_room = room_obj.search(old_prd_domain, limit=1)
                if prod_room and old_prod_room:
                    # Check for existing room lines.
                    srch_rmline = [('room_id', '=', old_prod_room.id),
                                   ('check_in', '=', self.checkin_date),
                                   ('check_out', '=', self.checkout_date),
                                   ]
                    rm_lines = reservation_line_obj.search(srch_rmline)
                    if rm_lines:
                        rm_line_vals = {'room_id': prod_room.id,
                                        'check_in': chkin,
                                        'check_out': chkout}
                        rm_lines.write(rm_line_vals)
        return super(HotelFolioLineExt, self).write(vals)


class HotelReservation(models.Model):

    _name = "hotel.reservation"
    _rec_name = "reservation_no"
    _description = "Booking"
    _order = 'reservation_no desc'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    reservation_no = fields.Char('Booking No', size=64, readonly=True)
    date_order = fields.Datetime('Date Ordered', readonly=True, required=True,
                                 index=True,
                                 default=(lambda *a: time.strftime(dt)))
    warehouse_id = fields.Many2one('stock.warehouse', 'Hotel', readonly=True,
                                   index=True,
                                   required=True, default=1,
                                   states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', 'Guest', readonly=True,
                                 index=True,
                                 required=True,
                                 states={'draft': [('readonly', False)]})
    pricelist_id = fields.Many2one('product.pricelist', 'Scheme',
                                   required=True, readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   help="Pricelist for current reservation.")
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         readonly=True,
                                         states={'draft':
                                                 [('readonly', False)]},
                                         help="Invoice address for "
                                         "current reservation.")
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       readonly=True,
                                       states={'draft':
                                               [('readonly', False)]},
                                       help="The name and address of the "
                                       "contact that requested the order "
                                       "or quotation.")
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          readonly=True,
                                          states={'draft':
                                                  [('readonly', False)]},
                                          help="Delivery address"
                                          "for current reservation. ")
    checkin = fields.Datetime('Arrival Date', required=True,
                              readonly=True,
                              default=(lambda *a: datetime.strftime((datetime.strptime(time.strftime(dt),dt)+timedelta(minutes=10)),dt)),
                              states={'draft': [('readonly', False)]})
    checkout = fields.Datetime('Departure Date', required=True,
                               readonly=True,
                               states={'draft': [('readonly', False)]})
    adults = fields.Integer('Adults', size=64, readonly=True,
                            states={'draft': [('readonly', False)]},
                            help='List of adults there in guest list. ')
    children = fields.Integer('Children', size=64, readonly=True,
                              states={'draft': [('readonly', False)]},
                              help='Number of children there in guest list.')
    reservation_line = fields.One2many('hotel_reservation.line', 'line_id',
                                       'Booking Room(s)',
                                       required=True,
                                       help='Hotel room reservation details.',
                                       readonly=True,
                                       states={'draft': [('readonly', False)]},
                                       )
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ('done', 'Done')],
                             'State', readonly=True,
                             default=lambda *a: 'draft')
    folio_id = fields.Many2many('hotel.folio', 'hotel_folio_reservation_rel',
                                'order_id', 'invoice_id', string='Folio')
    no_of_folio = fields.Integer('Folio', compute="_compute_folio_id")
    dummy = fields.Datetime('Dummy')

    # byte here
    reserve_type = fields.Selection([('Walkin', 'Walk In'),
                                    ('Reservation', 'Reservation')],
                                    string='Booking Type',
                                    required=True,
                                    default='Walkin',
                                    help='Select Walk In if the Guest is doing an immediate check in'
                                            'Select Reservation if guest making making a reservation to check in later',
                                    states={'draft': [('readonly', False)]})
    nights = fields.Integer('Enter Nights', help='Enter Number of Nights guest is staying for',
                            states={'draft': [('readonly', False)]})
    actual_nights = fields.Integer('Nights',
                                   help='Number of Nights guest is staying for',
                                   compute='compute_nights',
                                   readonly=True)

    @api.onchange('checkin', 'checkout', 'nights')
    def compute_nights(self):
        if self.checkin and self.checkout:
            diff = (datetime.strptime(self.checkout, dt) - datetime.strptime(self.checkin, dt)).days
            self.actual_nights = diff
        if self.nights >= 1 and self.checkin:
            checkout = datetime.strptime(self.checkin, dt)+timedelta(self.nights)
            self.checkout = checkout.strftime(dt)

    @api.multi
    def _compute_folio_id(self):
        folio_list = []
        for res in self:
            for folio in res.folio_id:
                folio_list.append(folio.id)
            folio_len = len(folio_list)
            res.no_of_folio = folio_len
        return folio_len

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for reserv_rec in self:
            if reserv_rec.state != 'draft':
                raise ValidationError(_('You cannot delete Booking in %s\
                                         state.') % (reserv_rec.state))
        return super(HotelReservation, self).unlink()

    @api.multi
    def copy(self):
        ctx = dict(self._context) or {}
        ctx.update({'duplicate': True})
        return super(HotelReservation, self.with_context(ctx)).copy()

    @api.constrains('reservation_line', 'adults', 'children')
    def check_reservation_rooms(self):
        '''
        This method is used to validate the reservation_line.
        -----------------------------------------------------
        @param self: object pointer
        @return: raise a warning depending on the validation
        '''
        ctx = dict(self._context) or {}
        for reservation in self:
            cap = 0
            for rec in reservation.reservation_line:
                if len(rec.reserve) == 0:
                    raise ValidationError(_('Please Select Rooms \
                    For Booking.'))
                for room in rec.reserve:
                    cap += room.capacity
            if not ctx.get('duplicate'):
                if (reservation.adults + reservation.children) > cap:
                    raise ValidationError(_('Room Capacity Exceeded \n Please \
                                            Select Rooms According to Members \
                                            Accomodation.'))
            if reservation.adults <= 0:
                raise ValidationError(_('Adults must be more than 0'))

    @api.constrains('checkin', 'checkout')
    def check_in_out_dates(self):
        """
        When date_order is less then check-in date or
        Checkout date should be greater than the check-in date.
        """
        if self.checkout and self.checkin:
            if self.checkin < self.date_order:
                raise ValidationError(_('Check-in date should be greater than \
                                         the current date.'))
            if self.checkout < self.checkin:
                raise ValidationError(_('Check-out date should be greater \
                                         than Check-in date.'))

    @api.model
    def _needaction_count(self, domain=None):
        """
         Show a count of draft state reservations on the menu badge.
         """
        return self.search_count([('state', '=', 'draft')])

    @api.onchange('checkout', 'checkin')
    def on_change_checkout(self):
        '''
        When you change checkout or checkin update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        checkout_date = time.strftime(dt)
        checkin_date = time.strftime(dt)
        if not (checkout_date and checkin_date):
            return {'value': {}}
        delta = timedelta(days=1)
        dat_a = time.strptime(checkout_date, dt)[:5]
        addDays = datetime(*dat_a) + delta
        self.dummy = addDays.strftime(dt)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the hotel reservation as well
        ---------------------------------------------------------------------
        @param self: object pointer
        '''
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice',
                                                'contact'])
            self.partner_invoice_id = addr['invoice']
            self.partner_order_id = addr['contact']
            self.partner_shipping_id = addr['delivery']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if not vals:
            vals = {}
        vals['reservation_no'] = vals['reserve_type'][0]+self.env['ir.sequence'].\
            next_by_code('hotel.reservation') or 'New'
        return super(HotelReservation, self).create(vals)

    @api.multi
    def check_overlap(self, date1, date2):
        date2 = datetime.strptime(date2, '%Y-%m-%d')
        date1 = datetime.strptime(date1, '%Y-%m-%d')
        delta = date2 - date1
        return set([date1 + timedelta(days=i) for i in range(delta.days + 1)])

    @api.multi
    def confirmed_reservation(self):
        """
        This method create a new record set for hotel room reservation line
        -------------------------------------------------------------------
        @param self: The object pointer
        @return: new record set for hotel room reservation line.
        """
        reservation_line_obj = self.env['hotel.room.reservation.line']
        vals = {}
        for reservation in self:
            reserv_checkin = datetime.strptime(reservation.checkin, dt)
            reserv_checkout = datetime.strptime(reservation.checkout, dt)
            room_bool = False
            for line_id in reservation.reservation_line:
                for room_id in line_id.reserve:
                    if room_id.room_reservation_line_ids:
                        for reserv in room_id.room_reservation_line_ids.\
                                search([('status', 'in', ('confirm', 'done')),
                                        ('room_id', '=', room_id.id)]):
                            check_in = datetime.strptime(reserv.check_in, dt)
                            check_out = datetime.strptime(reserv.check_out, dt)
                            if check_in <= reserv_checkin <= check_out:
                                room_bool = True
                            if check_in <= reserv_checkout <= check_out:
                                room_bool = True
                            if reserv_checkin <= check_in and \
                                    reserv_checkout >= check_out:
                                room_bool = True
                            mytime = "%Y-%m-%d"
                            r_checkin = datetime.strptime(reservation.checkin,
                                                          dt).date()
                            r_checkin = r_checkin.strftime(mytime)
                            r_checkout = datetime.\
                                strptime(reservation.checkout, dt).date()
                            r_checkout = r_checkout.strftime(mytime)
                            check_intm = datetime.strptime(reserv.check_in,
                                                           dt).date()
                            check_outtm = datetime.strptime(reserv.check_out,
                                                            dt).date()
                            check_intm = check_intm.strftime(mytime)
                            check_outtm = check_outtm.strftime(mytime)
                            range1 = [r_checkin, r_checkout]
                            range2 = [check_intm, check_outtm]
                            overlap_dates = self.check_overlap(*range1) \
                                & self.check_overlap(*range2)
                            overlap_dates = [datetime.strftime(dates,
                                                               '%d/%m/%Y') for
                                             dates in overlap_dates]
                            if room_bool:
                                raise ValidationError(_('You tried to Confirm '
                                                        'Booking with room'
                                                        ' those already '
                                                        'reserved in this '
                                                        'Booking Period. '
                                                        'Overlap Dates are '
                                                        '%s') % overlap_dates)
                            else:
                                self.state = 'confirm'
                                vals = {'room_id': room_id.id,
                                        'check_in': reservation.checkin,
                                        'check_out': reservation.checkout,
                                        'state': 'assigned',
                                        'reservation_id': reservation.id,
                                        }
                                room_id.write({'isroom': False,
                                               'status': 'occupied'})
                        else:
                            self.state = 'confirm'
                            vals = {'room_id': room_id.id,
                                    'check_in': reservation.checkin,
                                    'check_out': reservation.checkout,
                                    'state': 'assigned',
                                    'reservation_id': reservation.id,
                                    }
                            room_id.write({'isroom': False,
                                           'status': 'occupied'})
                    else:
                        self.state = 'confirm'
                        vals = {'room_id': room_id.id,
                                'check_in': reservation.checkin,
                                'check_out': reservation.checkout,
                                'state': 'assigned',
                                'reservation_id': reservation.id,
                                }
                        room_id.write({'isroom': False,
                                       'status': 'occupied'})
                    reservation_line_obj.create(vals)
        return True

    @api.multi
    def cancel_reservation(self):
        """
        This method cancel record set for hotel room reservation line
        ------------------------------------------------------------------
        @param self: The object pointer
        @return: cancel record set for hotel room reservation line.
        """
        room_res_line_obj = self.env['hotel.room.reservation.line']
        hotel_res_line_obj = self.env['hotel_reservation.line']
        self.state = 'cancel'
        room_reservation_line = room_res_line_obj.search([('reservation_id',
                                                           'in', self.ids)])
        room_reservation_line.write({'state': 'unassigned'})
        room_reservation_line.unlink()
        reservation_lines = hotel_res_line_obj.search([('line_id',
                                                        'in', self.ids)])
        for reservation_line in reservation_lines:
            reservation_line.reserve.write({'isroom': True,
                                            'status': 'available'})
        return True

    @api.multi
    def set_to_draft_reservation(self):
        self.state = 'draft'
        return True

    @api.multi
    def send_reservation_maill(self):
        '''
        This function opens a window to compose an email,
        template message loaded by default.
        @param self: object pointer
        '''
        assert len(self._ids) == 1, 'This is for a single id at a time.'
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = (ir_model_data.get_object_reference
                           ('hotel_reservation',
                            'mail_template_hotel_reservation')[1])
        except ValueError:
            template_id = False
        try:
            compose_form_id = (ir_model_data.get_object_reference
                               ('mail',
                                'email_compose_message_wizard_form')[1])
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'hotel.reservation',
            'default_res_id': self._ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_send': True,
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
            'force_send': True
        }

    @api.model
    def reservation_reminder_24hrs(self):
        """
        This method is for scheduler
        every 1day scheduler will call this method to
        find all tomorrow's reservations.
        ----------------------------------------------
        @param self: The object pointer
        @return: send a mail
        """
        now_str = time.strftime(dt)
        now_date = datetime.strptime(now_str, dt)
        ir_model_data = self.env['ir.model.data']
        template_id = (ir_model_data.get_object_reference
                       ('hotel_reservation',
                        'mail_template_reservation_reminder_24hrs')[1])
        template_rec = self.env['mail.template'].browse(template_id)
        for reserv_rec in self.search([]):
            checkin_date = (datetime.strptime(reserv_rec.checkin, dt))
            difference = relativedelta(now_date, checkin_date)
            if(difference.days == -1 and reserv_rec.partner_id.email and
               reserv_rec.state == 'confirm'):
                template_rec.send_mail(reserv_rec.id, force_send=True)
        return True

    @api.multi
    def create_folio(self):
        """
        This method is for create new hotel folio.
        -----------------------------------------
        @param self: The object pointer
        @return: new record set for hotel folio.
        """
        hotel_folio_obj = self.env['hotel.folio']
        room_obj = self.env['hotel.room']
        for reservation in self:
            folio_lines = []
            checkin_date = reservation['checkin']
            checkout_date = reservation['checkout']
            if not self.checkin < self.checkout:
                raise ValidationError(_('Checkout date should be greater \
                                         than the Check-in date.'))
            duration_vals = (self.onchange_check_dates
                             (checkin_date=checkin_date,
                              checkout_date=checkout_date, duration=False))
            duration = duration_vals.get('duration') or 0.0
            folio_vals = {
                'date_order': reservation.date_order,
                'warehouse_id': reservation.warehouse_id.id,
                'partner_id': reservation.partner_id.id,
                'pricelist_id': reservation.pricelist_id.id,
                'partner_invoice_id': reservation.partner_invoice_id.id,
                'partner_shipping_id': reservation.partner_shipping_id.id,
                'checkin_date': reservation.checkin,
                'checkout_date': reservation.checkout,
                'duration': duration,
                'reservation_id': reservation.id,
                'service_lines': reservation['folio_id']
            }
            for line in reservation.reservation_line:
                for r in line.reserve:
                    folio_lines.append((0, 0, {
                        'checkin_date': checkin_date,
                        'checkout_date': checkout_date,
                        'product_id': r.product_id and r.product_id.id,
                        'name': reservation['reservation_no'],
                        'price_unit': r.list_price,
                        'product_uom_qty': duration,
                        'is_reserved': True}))
                    res_obj = room_obj.browse([r.id])
                    res_obj.write({'status': 'occupied', 'isroom': False})
            folio_vals.update({'room_lines': folio_lines})
            folio = hotel_folio_obj.create(folio_vals)
            if folio:
                for rm_line in folio.room_lines:
                    rm_line.product_id_change()
            self._cr.execute('insert into hotel_folio_reservation_rel'
                             '(order_id, invoice_id) values (%s,%s)',
                             (reservation.id, folio.id))
            self.state = 'done'
        return True

    @api.multi
    def onchange_check_dates(self, checkin_date=False, checkout_date=False,
                             duration=False):
        '''
        This method gives the duration between check in checkout if
        customer will leave only for some hour it would be considers
        as a whole day. If customer will checkin checkout for more or equal
        hours, which configured in company as additional hours than it would
        be consider as full days
        --------------------------------------------------------------------
        @param self: object pointer
        @return: Duration and checkout_date
        '''
        value = {}
        configured_addition_hours = 0
        wc_id = self.warehouse_id
        whcomp_id = wc_id or wc_id.company_id
        if whcomp_id:
            configured_addition_hours = wc_id.company_id.additional_hours
        duration = 0
        if checkin_date and checkout_date:
            chkin_dt = datetime.strptime(checkin_date, dt)
            chkout_dt = datetime.strptime(checkout_date, dt)
            dur = chkout_dt - chkin_dt
            duration = dur.days + 1
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60))
                if additional_hours <= abs(configured_addition_hours * 60):
                    duration -= 1
        value.update({'duration': duration})
        return value


class HotelReservationLine(models.Model):

    _name = "hotel_reservation.line"
    _description = "Booking Line"

    name = fields.Char('Name', size=64)
    line_id = fields.Many2one('hotel.reservation')
    reserve = fields.Many2many('hotel.room',
                               'hotel_reservation_line_room_rel',
                               'hotel_reservation_line_id', 'room_id',
                               domain="[('isroom','=',True),\
                               ('categ_id','=',categ_id)]")
    categ_id = fields.Many2one('hotel.room.type', 'Room Type')

    @api.onchange('categ_id')
    def on_change_categ(self):
        '''
        When you change categ_id it check checkin and checkout are
        filled or not if not then raise warning
        -----------------------------------------------------------
        @param self: object pointer
        '''
        hotel_room_obj = self.env['hotel.room']
        hotel_room_ids = hotel_room_obj.search([('categ_id', '=',
                                                 self.categ_id.id)])
        room_ids = []
        if not self.line_id.checkin:
            raise ValidationError(_('Before choosing a room,\n You have to \
                                     select a Check in date or a Check out \
                                     date in the reservation form.'))
        for room in hotel_room_ids:
            assigned = False
            for line in room.room_reservation_line_ids:
                if line.status != 'cancel':
                    if(self.line_id.checkin <= line.check_in <=
                        self.line_id.checkout) or (self.line_id.checkin <=
                                                   line.check_out <=
                                                   self.line_id.checkout):
                        assigned = True
                    elif(line.check_in <= self.line_id.checkin <=
                         line.check_out) or (line.check_in <=
                                             self.line_id.checkout <=
                                             line.check_out):
                        assigned = True
            for rm_line in room.room_line_ids:
                if rm_line.status != 'cancel':
                    if(self.line_id.checkin <= rm_line.check_in <=
                       self.line_id.checkout) or (self.line_id.checkin <=
                                                  rm_line.check_out <=
                                                  self.line_id.checkout):
                        assigned = True
                    elif(rm_line.check_in <= self.line_id.checkin <=
                         rm_line.check_out) or (rm_line.check_in <=
                                                self.line_id.checkout <=
                                                rm_line.check_out):
                        assigned = True
            if not assigned:
                room_ids.append(room.id)
        domain = {'reserve': [('id', 'in', room_ids)]}
        return {'domain': domain}

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        hotel_room_reserv_line_obj = self.env['hotel.room.reservation.line']
        for reserv_rec in self:
            for rec in reserv_rec.reserve:
                hres_arg = [('room_id', '=', rec.id),
                            ('reservation_id', '=', reserv_rec.line_id.id)]
                myobj = hotel_room_reserv_line_obj.search(hres_arg)
                if myobj.ids:
                    rec.write({'isroom': True, 'status': 'available'})
                    myobj.unlink()
        return super(HotelReservationLine, self).unlink()


class HotelRoomReservationLine(models.Model):

    _name = 'hotel.room.reservation.line'
    _description = 'Hotel Room Booking'
    _rec_name = 'room_id'

    room_id = fields.Many2one('hotel.room', string='Room id')
    check_in = fields.Datetime('Check In Date', required=True)
    check_out = fields.Datetime('Check Out Date', required=True)
    state = fields.Selection([('assigned', 'Assigned'),
                              ('unassigned', 'Unassigned')], 'Room Status')
    reservation_id = fields.Many2one('hotel.reservation',
                                     string='Booking')
    status = fields.Selection(string='state', related='reservation_id.state')


class HotelRoom(models.Model):

    _inherit = 'hotel.room'
    _description = 'Hotel Room'

    room_reservation_line_ids = fields.One2many('hotel.room.reservation.line',
                                                'room_id',
                                                string='Room Reserve Line')

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for room in self:
            for reserv_line in room.room_reservation_line_ids:
                if reserv_line.status == 'confirm':
                    raise ValidationError(_('User is not able to delete the \
                                            room after the room in %s state \
                                            in reservation')
                                          % (reserv_line.status))
        return super(HotelRoom, self).unlink()

    @api.model
    def cron_room_line(self):
        """
        This method is for scheduler
        every 1min scheduler will call this method and check Status of
        room is occupied or available
        --------------------------------------------------------------
        @param self: The object pointer
        @return: update status of hotel room reservation line
        """
        reservation_line_obj = self.env['hotel.room.reservation.line']
        folio_room_line_obj = self.env['folio.room.line']
        now = datetime.now()
        curr_date = now.strftime(dt)
        for room in self.search([]):
            reserv_line_ids = [reservation_line.ids for
                               reservation_line in
                               room.room_reservation_line_ids]
            reserv_args = [('id', 'in', reserv_line_ids),
                           ('check_in', '<=', curr_date),
                           ('check_out', '>=', curr_date)]
            reservation_line_ids = reservation_line_obj.search(reserv_args)
            rooms_ids = [room_line.ids for room_line in room.room_line_ids]
            rom_args = [('id', 'in', rooms_ids),
                        ('check_in', '<=', curr_date),
                        ('check_out', '>=', curr_date)]
            room_line_ids = folio_room_line_obj.search(rom_args)
            status = {'isroom': True, 'color': 5}
            if reservation_line_ids.ids:
                status = {'isroom': False, 'color': 2}
            room.write(status)
            if room_line_ids.ids:
                status = {'isroom': False, 'color': 2}
            room.write(status)
            if reservation_line_ids.ids and room_line_ids.ids:
                raise ValidationError(_('Please Check Rooms Status \
                                         for %s.' % (room.name)))
        return True


class RoomReservationSummary(models.Model):

    _name = 'room.reservation.summary'
    _description = 'Room reservation summary'

    name = fields.Char('Booking Summary', default='Bookings Summary',
                       invisible=True)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    summary_header = fields.Text('Summary Header')
    room_summary = fields.Text('Room Summary')

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
        res = super(RoomReservationSummary, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=10)
        dt_to = to_dt.strftime(dt)
        res.update({'date_from': dt_from, 'date_to': dt_to})

        if not self.date_from and self.date_to:
            date_today = datetime.datetime.today()
            first_day = datetime.datetime(date_today.year,
                                          date_today.month, 1, 0, 0, 0)
            first_temp_day = first_day + relativedelta(months=1)
            last_temp_day = first_temp_day - relativedelta(days=1)
            last_day = datetime.datetime(last_temp_day.year,
                                         last_temp_day.month,
                                         last_temp_day.day, 23, 59, 59)
            date_froms = first_day.strftime(dt)
            date_ends = last_day.strftime(dt)
            res.update({'date_from': date_froms, 'date_to': date_ends})
        return res

    @api.multi
    def room_reservation(self):
        '''
        @param self: object pointer
        '''
        mod_obj = self.env['ir.model.data']
        if self._context is None:
            self._context = {}
        model_data_ids = mod_obj.search([('model', '=', 'ir.ui.view'),
                                         ('name', '=',
                                          'view_hotel_reservation_form')])
        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        return {'name': _('Reconcile Write-Off'),
                'context': self._context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hotel.reservation',
                'views': [(resource_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                }

    @api.onchange('date_from', 'date_to')
    def get_room_summary(self):
        '''
        @param self: object pointer
         '''
        res = {}
        all_detail = []
        room_obj = self.env['hotel.room']
        reservation_line_obj = self.env['hotel.room.reservation.line']
        folio_room_line_obj = self.env['folio.room.line']
        user_obj = self.env['res.users']
        date_range_list = []
        main_header = []
        summary_header_list = ['Rooms']
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_('Please Check Time period Date From can\'t \
                                   be greater than Date To !'))
            if self._context.get('tz', False):
                timezone = pytz.timezone(self._context.get('tz', False))
            else:
                timezone = pytz.timezone('UTC')
            d_frm_obj = datetime.strptime(self.date_from, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            d_to_obj = datetime.strptime(self.date_to, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            temp_date = d_frm_obj
            while(temp_date <= d_to_obj):
                val = ''
                val = (str(temp_date.strftime("%a")) + ' ' +
                       str(temp_date.strftime("%b")) + ' ' +
                       str(temp_date.strftime("%d")))
                summary_header_list.append(val)
                date_range_list.append(temp_date.strftime
                                       (dt))
                temp_date = temp_date + timedelta(days=1)
            all_detail.append(summary_header_list)
            room_ids = room_obj.search([])
            all_room_detail = []
            for room in room_ids:
                room_detail = {}
                room_list_stats = []
                room_detail.update({'name': room.name or ''})
                if not room.room_reservation_line_ids and \
                   not room.room_line_ids:
                    for chk_date in date_range_list:
                        room_list_stats.append({'state': 'Free',
                                                'date': chk_date,
                                                'room_id': room.id})
                else:
                    for chk_date in date_range_list:
                        ch_dt = chk_date[:10] + ' 23:59:59'
                        ttime = datetime.strptime(ch_dt, dt)
                        c = ttime.replace(tzinfo=timezone).\
                            astimezone(pytz.timezone('UTC'))
                        chk_date = c.strftime(dt)
                        reserline_ids = room.room_reservation_line_ids.ids
                        reservline_ids = (reservation_line_obj.search
                                          ([('id', 'in', reserline_ids),
                                            ('check_in', '<=', chk_date),
                                            ('check_out', '>=', chk_date),
                                            ('state', '=', 'assigned')
                                            ]))
                        if not reservline_ids:
                            sdt = dt
                            chk_date = datetime.strptime(chk_date, sdt)
                            chk_date = datetime.\
                                strftime(chk_date - timedelta(days=1), sdt)
                            reservline_ids = (reservation_line_obj.search
                                              ([('id', 'in', reserline_ids),
                                                ('check_in', '<=', chk_date),
                                                ('check_out', '>=', chk_date),
                                                ('state', '=', 'assigned')]))
                            for res_room in reservline_ids:
                                rrci = res_room.check_in
                                rrco = res_room.check_out
                                cid = datetime.strptime(rrci, dt)
                                cod = datetime.strptime(rrco, dt)
                                dur = cod - cid
                                if room_list_stats:
                                    count = 0
                                    for rlist in room_list_stats:
                                        cidst = datetime.strftime(cid, dt)
                                        codst = datetime.strftime(cod, dt)
                                        rm_id = res_room.room_id.id
                                        ci = rlist.get('date') >= cidst
                                        co = rlist.get('date') <= codst
                                        rm = rlist.get('room_id') == rm_id
                                        st = rlist.get('state') == 'Reserved'
                                        if ci and co and rm and st:
                                            count += 1
                                    if count - dur.days == 0:
                                        c_id1 = user_obj.browse(self._uid)
                                        c_id = c_id1.company_id
                                        con_add = 0
                                        amin = 0.0
                                        if c_id:
                                            con_add = c_id.additional_hours
#                                        When configured_addition_hours is
#                                        greater than zero then we calculate
#                                        additional minutes
                                        if con_add > 0:
                                            amin = abs(con_add * 60)
                                        hr_dur = abs((dur.seconds / 60))
#                                        When additional minutes is greater
#                                        than zero then check duration with
#                                        extra minutes and give the room
#                                        reservation status is reserved or
#                                        free
                                        if amin > 0:
                                            if hr_dur >= amin:
                                                reservline_ids = True
                                            else:
                                                reservline_ids = False
                                        else:
                                            if hr_dur > 0:
                                                reservline_ids = True
                                            else:
                                                reservline_ids = False
                                    else:
                                        reservline_ids = False
                        fol_room_line_ids = room.room_line_ids.ids
                        chk_state = ['draft', 'cancel']
                        folio_resrv_ids = (folio_room_line_obj.search
                                           ([('id', 'in', fol_room_line_ids),
                                             ('check_in', '<=', chk_date),
                                             ('check_out', '>=', chk_date),
                                             ('status', 'not in', chk_state)
                                             ]))
                        if reservline_ids or folio_resrv_ids:
                            room_list_stats.append({'state': 'Reserved',
                                                    'date': chk_date,
                                                    'room_id': room.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})
                        else:
                            room_list_stats.append({'state': 'Free',
                                                    'date': chk_date,
                                                    'room_id': room.id})

                room_detail.update({'value': room_list_stats})
                all_room_detail.append(room_detail)
            main_header.append({'header': summary_header_list})
            self.summary_header = str(main_header)
            self.room_summary = str(all_room_detail)
        return res


class QuickRoomReservation(models.TransientModel):
    _name = 'quick.room.reservation'
    _description = 'Quick Room Booking'

    partner_id = fields.Many2one('res.partner', string="Customer",
                                 required=True)
    check_in = fields.Datetime('Check In', required=True)
    check_out = fields.Datetime('Check Out', required=True)
    room_id = fields.Many2one('hotel.room', 'Room', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Hotel', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'pricelist')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         required=True)
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       required=True)
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          required=True)
    adults = fields.Integer('Adults', size=64)
    reserve_type = fields.Selection([('Walkin', 'Walk In'),
                                     ('Reservation', 'Reservation')],
                                    string='Booking Type',
                                    required=True,
                                    default='Walkin',
                                    help='Select Walk In if the Guest is doing an immediate check in'
                                         'Select Reservation if guest making making a reservation to check in later',
                                    states={'draft': [('readonly', False)]})

    @api.onchange('check_out', 'check_in')
    def on_change_check_out(self):
        '''
        When you change checkout or checkin it will check whether
        Checkout date should be greater than Checkin date
        and update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.check_out and self.check_in:
            if self.check_out < self.check_in:
                raise ValidationError(_('Checkout date should be greater \
                                         than Checkin date.'))

    @api.onchange('partner_id')
    def onchange_partner_id_res(self):
        '''
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the hotel reservation as well
        ---------------------------------------------------------------------
        @param self: object pointer
        '''
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice',
                                                'contact'])
            self.partner_invoice_id = addr['invoice']
            self.partner_order_id = addr['contact']
            self.partner_shipping_id = addr['delivery']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

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
        res = super(QuickRoomReservation, self).default_get(fields)
        if self._context:
            keys = self._context.keys()
            if 'date' in keys:
                res.update({'check_in': self._context['date']})
            if 'room_id' in keys:
                roomid = self._context['room_id']
                res.update({'room_id': int(roomid)})
        return res

    @api.multi
    def room_reserve(self):
        """
        This method create a new record for hotel.reservation
        -----------------------------------------------------
        @param self: The object pointer
        @return: new record set for hotel reservation.
        """
        hotel_res_obj = self.env['hotel.reservation']
        for res in self:
            rec = (hotel_res_obj.create
                   ({'partner_id': res.partner_id.id,
                     'reserve_type': res.reserve_type,
                     'partner_invoice_id': res.partner_invoice_id.id,
                     'partner_order_id': res.partner_order_id.id,
                     'partner_shipping_id': res.partner_shipping_id.id,
                     'checkin': res.check_in,
                     'checkout': res.check_out,
                     'warehouse_id': res.warehouse_id.id,
                     'pricelist_id': res.pricelist_id.id,
                     'adults': res.adults,
                     'reservation_line': [(0, 0,
                                           {'reserve': [(6, 0,
                                                         [res.room_id.id])],
                                            'name': (res.room_id and
                                                     res.room_id.name or '')
                                            })]
                     }))
        return rec
