# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.safe_eval import safe_whitelist

from . import models
from . import wizards

safe_whitelist.add_function('odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.L10n_Es_Edi_TbaiDocument._generate_xml.<locals>.*')
