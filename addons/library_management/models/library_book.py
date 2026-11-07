from odoo import _, fields, models
from odoo.exceptions import UserError


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'name'

    name = fields.Char(string='Title', required=True)
    author = fields.Char()
    isbn = fields.Char(string='ISBN')
    category = fields.Selection([
        ('fiction', 'Fiction'),
        ('non_fiction', 'Non-Fiction'),
        ('technology', 'Technology'),
    ])
    state = fields.Selection(
        [('available', 'Available'), ('borrowed', 'Borrowed')],
        default='available', required=True, copy=False,
    )
    member_id = fields.Many2one('library.member', string='Borrowed By', copy=False)
    borrow_date = fields.Date(copy=False)

    _isbn_unique = models.Constraint(
        'unique(isbn)',
        'This ISBN already exists for another book!',
    )

    def action_borrow(self):
        for book in self:
            if not book.member_id:
                raise UserError(_('Please select a member before borrowing this book.'))
            book.state = 'borrowed'
            book.borrow_date = fields.Date.context_today(book)

    def action_return(self):
        self.write({
            'state': 'available',
            'member_id': False,
            'borrow_date': False,
        })
