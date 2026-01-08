# -*- coding: utf-8 -*-
# Internal References: odoo.http for controller/routing, odoo.http.request for request-specific context
from odoo import http
from odoo.http import request

class LibraryController(http.Controller):

    @http.route('/library/books', type='json', auth='user', methods=['GET'], website=False)
    def list_books(self, **kw):
        """Simple JSON endpoint to list active books."""
        # Internal Reference: request.env gives access to the ORM environment for the current request
        # Internal Reference: request.env['model.name'] accesses the model from the registry
        try:
            # Internal Reference: search_read combines search and read in one optimized call
            books = request.env['library.book'].search_read(
                domain=[('active', '=', True)], # Basic filter
                fields=['id', 'name'],          # Fields to return
                limit=50,                       # Basic pagination
                order='name'
            )
            return {'status': 'success', 'books': books}
        except Exception as e:
            # Basic error handling
            return {'status': 'error', 'message': str(e)}

    # Example of a simple HTML route (optional)
    # @http.route('/library/hello', type='http', auth='public', website=True)
    # def hello_page(self, **kw):
    #     return request.render('library_simple.hello_template') # Needs a QWeb template