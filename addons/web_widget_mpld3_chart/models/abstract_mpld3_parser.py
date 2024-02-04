# Copyright 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

try:
    import mpld3
    from bs4 import BeautifulSoup
except (ImportError, IOError) as err:
    _logger.debug(err)


class AbstractMpld3Parser(models.AbstractModel):

    _name = "abstract.mpld3.parser"
    _description = "Utility to parse ploot figure to json data for widget Mpld3"

    @api.model
    def convert_figure_to_json(self, figure):
        html_string = mpld3.fig_to_html(figure, no_extras=True, include_libraries=False)
        soup = BeautifulSoup(html_string, "lxml")
        json_data = {
            "div": str(soup.div),
            "script": soup.script.decode_contents(),
        }
        return json_data
