from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Internal Reference: All models inherit from odoo.models.Model or odoo.models.TransientModel/AbstractModel
class LibraryBook(models.Model):
    """Represents a book in the library."""
    # Internal Reference: _name defines the unique model identifier used in relations, views, etc.
    _name = 'library.book'
    _description = 'Library Book'
    # Internal Reference: _order defines default sorting for searches
    _order = 'name'

    name = fields.Char(string='Title', required=True, index=True)
    # Internal Reference: Common practice for soft delete/archiving
    active = fields.Boolean(string='Active?', default=True)
    description = fields.Text(string='Synopsis')

    # Simple business logic: Constraint
    @api.constrains('name')
    def _check_name_not_empty(self):
        for record in self:
            if not record.name or not record.name.strip():
                # Internal Reference: odoo.exceptions contains standard Odoo exceptions
                raise ValidationError(_("Book title cannot be empty."))

    # Simple business logic: Override copy method
    # Internal Reference: Methods often return self for chaining
    def copy(self, default=None):
        """Override copy to modify the name."""
        # Internal Reference: Accessing super() calls the parent method from odoo.models.BaseModel
        copied_book = super(LibraryBook, self).copy(default=default)
        copied_book.name = _("%s (Copy)", self.name)
        return copied_book