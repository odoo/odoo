from dateutil.utils import today

from odoo import fields , api , models
from datetime import date, timedelta
import logging

from odoo.api import ValuesType, Self
from odoo.exceptions import UserError
from odoo import models, fields ,api
from datetime import date

from odoo.tools import float_compare
from odoo.tools.float_utils import float_is_zero

class library_mangement_borrow(models.Model):
    _name = "library.mangement.borrow"
    _description = "represnt the action borrow between the customer and the books"
    _logger = logging.getLogger(__name__)
    book_id= fields.Many2one(
        'library.mangement.book',
        string="Book name",
        required=True
    )

    customer_id= fields.Many2one(
        'library.mangement.customer',
        string="Customer name",
        required=True
    )
    browwed_date=fields.Date(
        default = fields.Date.today()- timedelta(days=60)
        ,required = True
    )
    return_date= fields.Date(
        default= fields.Date.today()- timedelta(days=30)
        ,required = True
    )
    state = fields.Selection(
        selection=[
            ('proposed', 'Proposed'),
            ('accepted', 'Accepted'),
            ('refused',  'Refused'),
            ('returned', 'Returned'),
        ],
        default='proposed',
        string='Status',
        required=True
    )
    payment= fields.Float(
        compute='_compute_total_payment',
        readonly=True,
        string ="Payment for borrow",
        store=True
    )
    check_date_validation=fields.Integer(
        compute='_compute_valid_date',
        store=True
    )
    _sql_constraints = [
        ('Invalid_date', 'CHECK(check_date_validation < 0)',
         'the browwed date sould comes before the return data or at least same date.')
    ]
    @api.depends('return_date', 'state')
    def _compute_total_payment(self):
        for record in self:
            today = fields.Date.today()
            delta_days = (today - record.return_date).days
            record.payment = delta_days * 0.5 if delta_days > 0 and record.state == 'accepted' else 0

    @api.depends('browwed_date','return_date')
    def _compute_valid_date(self):
        for recocrd in self:
            recocrd.check_date_validation=(recocrd.return_date-recocrd.browwed_date).days


    def action_confirm(self):
        for record in self:
            if record.state != 'proposed':
                raise UserError("Only proposed offer can by accepted")

            book= record.book_id
            if not book.quantities:
                raise UserError("No books founds!!")

            try:
                qty=int(book.quantities)
            except:
                raise UserError("Quantities must be integer")

            if(qty <= 0):
                raise UserError("NO copies left to boroow")
            book.quantities= qty-1
            record.state='accepted'

    def action_cancel(self):
        for record in self:
            record.state='refused'

    def action_return(self):
        for record in self:
            if record.state != 'accepted':
                raise UserError('Can not return the book when the borrow action is not accepted')
            try:
                book=record.book_id
                qty= int(book.quantities)
                book.quantities=qty+1
                record.state='returned'
            except:
                raise UserError("There is error in the return transaction")

    @api.onchange("state")
    def _onchagne_state(self):
        for record in self:
            if(record.state=='returned'):
                if(record.payment !=0):
                    return {'warning': {
                    'title': ("Garden Setted True"),
                    'message': ('You need to Set the area and orentation of the garden')}}