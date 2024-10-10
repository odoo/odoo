# -*- coding: utf-8 -*-

from odoo import models, fields
from datetime import datetime
from PIL import ImageFont, ImageDraw, Image
from odoo.tools.misc import file_path


class res_company(models.Model):
    _inherit = "res.company"

    # This field needs to be overridden with `selection_add` in the modules which intends to add report layouts.
    # The xmlID of all the report actions which are actually Check Layouts has to be kept as key of the selection.
    account_check_printing_layout = fields.Selection(
        string="Check Layout",
        selection=[
            ('disabled', 'None'),
            ('account_check_printing.action_print_check', 'Custom'),
        ],
        default='disabled',
        help="Select the format corresponding to the check paper you will be printing your checks on.\n"
             "In order to disable the printing feature, select 'None'.",
    )
    account_check_printing_date_label = fields.Boolean(
        string='Print Date Label',
        default=True,
        help="This option allows you to print the date label on the check as per CPA.\n"
             "Disable this if your pre-printed check includes the date label.",
    )
    account_check_printing_multi_stub = fields.Boolean(
        string='Multi-Pages Check Stub',
        help="This option allows you to print check details (stub) on multiple pages if they don't fit on a single page.",
    )
    account_check_printing_margin_top = fields.Float(
        string='Check Top Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
    )
    account_check_printing_margin_left = fields.Float(
        string='Check Left Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
    )
    account_check_printing_margin_right = fields.Float(
        string='Right Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
    )
    account_check_layout_format_id = fields.Many2one('account.check.layout.format', readonly=False)

    def write(self, vals):
        result = super().write(vals)
        self._paper_format()
        return result

    def _paper_format(self):
        paper_format = self.env['report.paperformat'].search([('name', '=', 'Check Paper Format')], limit=1)
        if paper_format:
            paper_format.write({
                'page_height': self.account_check_layout_format_id.paper_height if self.account_check_layout_format_id.paper_format == 'custom' else 0.0,
                'page_width': self.account_check_layout_format_id.paper_width if self.account_check_layout_format_id.paper_format == 'custom' else 0.0,
                'format': self.account_check_layout_format_id.paper_format,
                'orientation': self.account_check_layout_format_id.check_orientation,
            })

    def formatted_date_with_seperator(self, date):
        date_obj = datetime.strptime(date, '%m/%d/%Y')
        date_seperator = self.account_check_layout_format_id.check_date_seperator or ''
        day_str = f"{date_obj.day:02}"
        month_str = f"{date_obj.month:02}"
        year_str = f"{date_obj.year:04}"
        year_short_str = f"{date_obj.year % 100:02}"

        date_string = f"{day_str}{date_seperator}{month_str}{date_seperator}{year_str}"
        if self.account_check_layout_format_id.check_date_format == 'mmddyyyy':
            date_string = f"{month_str}{date_seperator}{day_str}{date_seperator}{year_str}"
        elif self.account_check_layout_format_id.check_date_format == 'yyyymmdd':
            date_string = f"{year_str}{date_seperator}{month_str}{date_seperator}{day_str}"
        elif self.account_check_layout_format_id.check_date_format == 'mmddyy':
            date_string = f"{month_str}{date_seperator}{day_str}{date_seperator}{year_short_str}"
        elif self.account_check_layout_format_id.check_date_format == 'ddmmyy':
            date_string = f"{day_str}{date_seperator}{month_str}{date_seperator}{year_short_str}"
        elif self.account_check_layout_format_id.check_date_format == 'yymmdd':
            date_string = f"{year_short_str}{date_seperator}{month_str}{date_seperator}{day_str}"

        return date_string

    def text_length_in_mm(self, text, dpi):
        # Create a temporary image to get the drawing context
        img = Image.new('RGB', (1, 1))  # 1x1 pixel image
        draw = ImageDraw.Draw(img)

        lato_path = 'web/static/fonts/lato/Lato-Reg-webfont.ttf'
        # Load the font
        font = ImageFont.truetype(file_path(lato_path), 12)

        # Get the width of the text
        text_width, _ = draw.textlength(text, font=font)

        # Convert width from pixels to mm
        width_in_mm = (text_width / dpi) * 25.4

        return width_in_mm

    def get_aiw_lines(self, amount_in_word):
        dpi = self.env['report.paperformat'].search([('name', '=', 'Check Paper Format')], limit=1).dpi
        line1_width = self.account_check_layout_format_id.aiw_line1_width_area
        line2_width = self.account_check_layout_format_id.aiw_line2_width_area
        line1, line2 = '', ''
        words = amount_in_word.split() if self.account_check_layout_format_id.aiw_currency_name == 'yes' else amount_in_word.split()[:-1]

        for i in range(len(words)):
            if self.text_length_in_mm(line1 + words[i] + ' ', dpi) <= line1_width:
                line1 += words[i] + ' '
            elif self.text_length_in_mm(line2 + words[i] + ' ', dpi) <= line2_width:
                line2 += words[i] + ' '
            else:
                break

        return [line1, line2]
