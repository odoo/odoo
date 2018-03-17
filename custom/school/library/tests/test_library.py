# See LICENSE file for full copyright and licensing details.

from odoo.tests import common
import time


class TestLibrary(common.TransactionCase):

    def setUp(self):
        super(TestLibrary, self).setUp()
        self.product_product_obj = self.env['product.product']
        self.library_rack_obj = self.env['library.rack']
        self.product_lang_obj = self.env['product.lang']
        self.library_author_obj = self.env['library.author']
        self.book_editor_obj = self.env['book.editor']
        self.library_card_obj = self.env['library.card']
        self.purchase_order_obj = self.env['purchase.order']
        self.purchase_order_line_obj = self.env['purchase.order.line']
        self.library_book_request_obj = self.env['library.book.request']
        self.library_book_issue_obj = self.env['library.book.issue']
        self.stock_picking_obj = self.env['stock.picking']
        self.immideate_transfer = self.env['stock.immediate.transfer']
        self.student_id = self.env.ref('school.demo_student_student_5')
        self.school_standard = self.env.ref('school.demo_school_standard_2')
        self.standard = self.env.ref('school.demo_standard_standard_2')
        self.product = self.env.ref('library.library_product_b2')
        self.res_partner = self.env.ref('base.res_partner_1')
        self.category = self.env.ref('product.product_category_1')
        self.company_id = self.env.ref('school.demo_school_1')
        self.product_book = self.env.ref('library.product_product_b1')
        self.prd_uom = self.env.ref('product.product_uom_unit')
        # Create library rack
        self.library_rack = self.library_rack_obj.\
            create({'name': 'Rack34',
                    'code': 'rack34',
                    'active': True
                    })
        # Create product language
        self.product_lang = self.product_lang_obj.\
            create({'code': 'LG4',
                    'name': 'Hindi',
                    })
        # Create library author
        self.library_author = self.library_author_obj.\
            create({'name': 'NCERT'
                    })
        # Create product
        categ = self.env['product.category'].search([('name', '=', 'Books')])
        self.product_product = self.product_product_obj.\
            create({'name': 'Java',
                    'categ_id': categ.id,
                    'type': 'product',
                    'day_to_return_book': 10,
                    'weight': 1.23,
                    'fine_lost': 100,
                    'fine_late_return': 100,
                    'nbpage': 344,
                    'availability': 'notavailable',
                    'num_edition': 3
                    })
        # Create editior
        self.book_editor = self.book_editor_obj.\
            create({'name': 'S.S Prasad',
                    'book_id': self.product_product.id
                    })
        # Create library card
        self.library_card = self.library_card_obj.\
            create({'code': 'C0056',
                    'user': 'student',
                    'book_limit': 10,
                    'student_id': self.student_id.id,
                    'roll_no': 2,
                    'standard_id': self.school_standard.id,
                    })
        self.library_card._compute_name()
        # Create purchase order
        self.purchase_order = self.purchase_order_obj.\
            create({'partner_id': self.res_partner.id,
                    'date_order': time.strftime('06-29-2017 16:58:10'),
                    'date_planned': time.strftime('06-29-2017 16:58:10'),
                    })
        # Create purchase order line
        self.purchase_order_line = self.purchase_order_line_obj.\
            create({'product_id': self.product_product.id,
                    'name': 'Java Book',
                    'date_planned': time.strftime('06-29-2017 16:58:10'),
                    'company_id': self.company_id.id,
                    'product_qty': 10.0,
                    'price_unit': 250,
                    'product_uom': self.prd_uom.id,
                    'order_id': self.purchase_order.id
                    })
        self.purchase_order.button_confirm()
        self.purchase_order.action_view_picking()
        self.purchase_order_line.onchange_product_id()
        self.stock_picking = self.stock_picking_obj.\
            search([('origin', '=', self.purchase_order.name)])
        self.stock_picking.do_new_transfer()
        self.imm = self.immideate_transfer.\
            create({'pick_id': self.stock_picking.id})
        for rec in self.imm:
            rec.process()
        # Book request created
        self.library_book_request = self.library_book_request_obj.\
            create({'req_id': 'New',
                    'type': 'existing',
                    'card_id': self.library_card.id,
                    'name': self.product_product.id,
                    'book_return_days': 10
                    })
        self.library_book_request._compute_bname()
        self.library_book_request.draft_book_request()
        self.library_book_request.confirm_book_request()
        self.library_book_request.cancle_book_request()
        # Book issue created
        self.library_book_issue = self.library_book_issue_obj.\
            create({'issue_code': 'L097',
                    'name': self.product_product.id,
                    'card_id': self.library_card.id,
                    'user': 'Student',
                    'student_id': self.student_id.id,
                    'standard_id': self.standard.id,
                    'roll_no': 2,
                    'actual_return_date': time.strftime('06-29-2017 16:58:10'),
                    })
        self.library_book_issue.onchange_day_to_return_book()
        self.library_book_issue._compute_return_date()
        self.library_book_issue._compute_penalty()
        self.library_book_issue._compute_lost_penalty()
        self.library_book_issue._check_issue_book_limit()
        self.library_book_issue.onchange_card_issue()
        self.library_book_issue.draft_book()
        self.library_book_issue.issue_book()
        self.library_book_issue.reissue_book()
        self.library_book_issue.return_book()
        self.library_book_issue.cancel_book()

    def test_exam(self):
        self.assertEqual(self.library_card.student_id.state, 'done')
        self.assertEqual(self.library_book_issue.student_id.state, 'done')
