from odoo import models


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _get_exchanged_document_vals(self, invoice):
        # Extend `account_edi_xml_cii` to add mandatory default notes [BR-FR-05]
        result = super()._get_exchanged_document_vals(invoice)

        result['included_note_list'].extend([
            {
                'subject_code': code,
                'content': content,
            } for code, content in invoice._l10n_fr_pdp_get_default_notes().items()
        ])

        return result

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _cii_get_included_note_node(self, vals):
        # EXTENDS account.edi.cii
        nodes = super()._cii_get_included_note_node(vals)

        # [BR-FR-MAP-18] EN16931 caps the Note (BT-22) to 1024 characters.
        for node in nodes:
            if node['ram:Content']:
                node['ram:Content']['_text'] = node['ram:Content']['_text'][:1024]

        return nodes

    def _cii_get_line_specified_trade_product_node(self, vals, base_line):
        # EXTENDS account.edi.cii
        node = super()._cii_get_line_specified_trade_product_node(vals, base_line)

        # [BR-FR-MAP-17] EN16931 caps the Item name (BT-153) to 255 characters.
        if node['ram:Name']:
            node['ram:Name']['_text'] = node['ram:Name']['_text'][:255]

        return node

    def _cii_get_postal_trade_address_node(self, vals, address_values):
        # EXTENDS account.edi.cii
        node = super()._cii_get_postal_trade_address_node(vals, address_values)

        # [BR-FR-MAP-17/BR-FR-MAP-19] EN16931 caps these address lines to 255 characters (postal code: 10).
        for field in ('ram:LineOne', 'ram:LineTwo', 'ram:CityName'):
            if node.get(field):
                node[field]['_text'] = node[field]['_text'][:255]

        if node['ram:PostcodeCode']:
            node['ram:PostcodeCode']['_text'] = node['ram:PostcodeCode']['_text'][:10]

        return node
