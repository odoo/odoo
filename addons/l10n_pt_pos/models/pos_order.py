from odoo import models, fields


class PosOrder(models.Model):
    _name = "pos.order"

    inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)

    def hash_values(self, previous_hash, version="last")
        if version == "last":
            version  == "pt1"
        hash_values = {
            "version" = version,
        }
        if version == "pt1":
            sequence_prefix = ''.join(self.name.split('/')[:-1]).replace(' ','')
            sequence_postfix = self.name.split('/')[-1]
            docs_to_sign = [{
                'id': self.id,
                'secure_sequence_number': self.id
                'date': self.date.isoformat(timespec='days'), # TODO TZ portugal
                'system_entry_date': self.create_date.isoformat(timespec='seconds'),
                'l10n_pt_document_number': "FS " + sequence_prefix + "/" + sequence_postfix, # SUB
                'gross_total': float_repr(self.amount_total, 2),
                'previous_signature': previous_hash
            }]
            try:
                endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', DEFAULT_ENDPOINT)
                params = {
                    'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                    'documents': docs_to_sign,
                }
                response = requests.post(f'{endpoint}/sign_documents', json={'params': params}, timeout=5000)
                if not response.ok:
                    raise ConnectionError
                result = response.json().get('result')
                if result.get('error'):
                    raise Exception(result['error'])
                for record_id, record_info in result.items():
                    hash_values["inalterable_hash"] = record_info['signature']
                    hash_values["l10n_pt_private_key_version"] = int(record_info['signature_version'])
            except ConnectionError as e:
                _logger.error("Error while contacting the IAP endpoint: %s", e)
                raise UserError(_("Unable to connect to the IAP endpoint to sign the documents. Please check your internet connection."))
            except Exception as e:
                _logger.error("An error occurred when signing the document: %s", e)
                raise UserError(_("An error occurred when signing the document: %s", e))
        return hash_values

    def hash_compute(self):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        prev = self.sudo().search([('config_id', '=', self.config_id.id), ('state', 'in', ['paid','done','invoiced'])], order="id DESC", limit=1)
        prev_hash = ""
        if prev:
            prev_hash = prev.inalterable_hash
        return self.hash_values(previous_hash)

    def _process_order(self, order, draft, existing_order):
        order_id = super()._process_order(self, order, draft, existing_order)
        order = self.browse(order_id)
        hash_values["inalterable_hash"] = "$%s$%s" % (hash_values.pop('version'), hash_values["inalterable_hash"])
        order.write(hash_values)
        return pos_order.id

