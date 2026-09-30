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
            if (
                (note_node := node['ram:Content'])
                and isinstance(note_node['_text'], str)
            ):
                note_node['_text'] = note_node['_text'][:1024]

        return nodes

    def _cii_get_line_specified_trade_product_node(self, vals, base_line):
        # EXTENDS account.edi.cii
        node = super()._cii_get_line_specified_trade_product_node(vals, base_line)

        # [BR-FR-MAP-17] EN16931 caps the Item name (BT-153) to 255 characters.
        if (
            (item_name_node := node.get('ram:Name'))
            and isinstance(item_name_node['_text'], str)
        ):
            item_name_node['_text'] = item_name_node['_text'][:255]

        return node

    def _cii_get_postal_trade_address_node(self, vals, address_values):
        # EXTENDS account.edi.cii
        node = super()._cii_get_postal_trade_address_node(vals, address_values)

        # [BR-FR-MAP-17/BR-FR-MAP-19] EN16931 caps these address lines to 255 characters (postal code: 10).
        for field in ('ram:LineOne', 'ram:LineTwo', 'ram:CityName'):
            if node.get(field) and isinstance(node[field]['_text'], str):
                node[field]['_text'] = node[field]['_text'][:255]

        if (
            (postcode_node := node['ram:PostcodeCode'])
            and isinstance(postcode_node['_text'], str)
        ):
            postcode_node['_text'] = postcode_node['_text'][:10]

        return node
