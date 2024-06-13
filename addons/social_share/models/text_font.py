import logging
from io import BytesIO

from odoo import _, api, exceptions, fields, models

try:
    from fontTools.ttLib import TTFont
    TTFONT_INSTALLED = True
except ImportError:
    TTFONT_INSTALLED = False


_logger = logging.getLogger(__name__)

class TextFont(models.Model):
    _name = 'social.share.text.font'
    _description = 'Text Font'
    _order = 'sequence, id'

    _inherits = {'ir.attachment': 'attachment_id'}

    attachment_id = fields.Many2one('ir.attachment', required=True, ondelete="cascade")
    # string where pairs of contiguous characters (a, b) delimit the smallest and biggest character in a range of contiguous characters
    # e.g. "13adffxz" represents the following ranges: 123 abcd f xyz
    character_ranges = fields.Char(compute="_compute_characters", readonly=False, store=True)
    excluded_character_ranges = fields.Char()
    force_font_size = fields.Integer()
    sequence = fields.Integer()
    is_fallback = fields.Boolean(default=True)

    @api.constrains('character_ranges', 'excluded_character_ranges')
    def _check_ranges_evaluate(self):
        for font in self:
            if len(font.character_ranges or '') % 2 != 0 and len(font.excluded_character_ranges or '') % 2 != 0:
                raise exceptions.ValidationError(_("Character ranges must be paired."))

    @api.depends('checksum')
    def _compute_characters(self):
        if not TTFONT_INSTALLED:
            # don't do anything as they may have been precomputed
            _logger.warning("Fonttools is not installed. social_share will be unable to automatically fetch the correct fonts.")
            return
        for font in self:
            # null and \1 are not render-able so no font should have it
            prev = range_start = 0
            ranges = ""
            for integer in TTFont(BytesIO(font.raw)).getBestCmap().keys():
                if integer - prev > 1:
                    if range_start == prev:
                        char = chr(range_start)
                        ranges += char + char
                    else:
                        ranges += chr(range_start) + chr(prev)
                    range_start = integer
                prev = integer
            ranges = ranges[2:]
            font.character_ranges = ranges
