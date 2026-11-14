from odoo import api, fields, models
from odoo.tools.sql import column_exists


class UniversitySubjectBook(models.Model):
    _name = "university.subject.book"
    _description = "Subject Textbook Link"
    _order = "sequence, id"

    subject_id = fields.Many2one(
        "university.subject",
        string="Subject",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Textbook",
        required=True,
        domain="[('is_textbook', '=', True)]",
        ondelete="restrict",
        index=True,
    )
    book_type = fields.Selection(
        [
            ("required", "Required"),
            ("recommended", "Recommended"),
        ],
        string="Book Type",
        default="required",
        required=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    note = fields.Char(string="Note")

    _subject_product_uniq = models.Constraint(
        "UNIQUE(subject_id, product_tmpl_id)",
        "This textbook is already linked to this subject.",
    )

    @api.model
    def _migrate_legacy_subject_books(self):
        """Migrate any legacy rows having product_id to product_tmpl_id if legacy column exists."""
        if column_exists(self.env.cr, "university_subject_book", "product_id"):
            self.env.cr.execute("""
                UPDATE university_subject_book usb
                SET product_tmpl_id = pp.product_tmpl_id
                FROM product_product pp
                WHERE usb.product_id = pp.id AND usb.product_tmpl_id IS NULL;
            """)
        if (
            column_exists(self.env.cr, "university_subject_book", "product_tmpl_id")
            and column_exists(self.env.cr, "product_template", "is_textbook")
        ):
            self.env.cr.execute("""
                UPDATE product_template pt
                SET is_textbook = TRUE
                FROM university_subject_book usb
                WHERE usb.product_tmpl_id = pt.id AND NOT COALESCE(pt.is_textbook, FALSE);
            """)
        return True
