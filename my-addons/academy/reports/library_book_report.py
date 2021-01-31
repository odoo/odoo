from odoo import models, fields

class BookReport(models.Model):
    _name = 'academy.library.book.report'
    _description = 'Book Report'
    _auto = False

    name = fields.Char('name')
   #publisher_id = fields.Many2one('res.partner')

    date_published = fields.Date("date_published")

    def init(self):

        self.env.cr.execute("""

            CREATE OR REPLACE VIEW academy_library_book_report AS

            (SELECT *,now() date_published

            FROM academy_teachers

            WHERE 1=1)

        """)

    def do_advanced_query(self):
        print('2223333')
        return {
            'warning': {
                'title': '提示',
                'message': '知道🌶啦！'
            }
        }
