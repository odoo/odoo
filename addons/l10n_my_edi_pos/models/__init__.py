# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Note: using two files for `myinvois.document` so that we can keep the general logic and the logic specific to PoS
# separate, will make it easier when moving the document to the l10n_my_edi module in master.
from . import account_edi_xml_ubl_my
from . import account_tax
from . import myinvois_document
from . import myinvois_document_pos
from . import pos_order
