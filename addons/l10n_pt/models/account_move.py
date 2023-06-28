DEFAULT_ENDPOINT = 'http://l10n-pt.api.odoo.com/iap/l10n_pt'

class AccountMove(models.Model):
    _name = "account.move"

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------
    def _hash_fields(self):
        return ['name', 'date', 'create_date']

    def l10pt_hash_string(self, previous_hash, version="last")
        # Pourt info
        #date = self.l10n_pt_date.strftime('%Y-%m-%d')
        #system_entry_date = self.create_date.strftime("%Y-%m-%dT%H:%M:%S")
        #gross_total = float_repr(self.l10n_pt_gross_total, 2)
        #previous_hash = previous_hash or self._get_blockchain_record_previous_hash()
        #message = f"{date};{system_entry_date};{self.l10n_pt_document_number};{gross_total};{previous_hash}"
        #return self._l10n_pt_sign_message(message)

    def hash_values(self, previous_hash, version="last")
        if version == "last":
            version  == "pt1"
        hash_values = {
            "version" = version,
        }
        if version == "pt1":
            # To make odo happy $format$value unix style
            previous_hash = previous_hash.split("$")[2]
            docs_to_sign = [{
                'id': self.id,
                'secure_sequence_number': self.sequence_number
                'date': self.date.isoformat(),
                'system_entry_date': self.create_date.isoformat(timespec='seconds'),
                'l10n_pt_document_number': "F " + re.sub(self.sequence_prefix, r"[/ ]", "") + "/" + self.name[len(self.sequence_prefix)+1],
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

    #    """
    #    Technical requirements from the Portuguese tax authority can be found at page 13 of the following document:
    #    https://info.portaldasfinancas.gov.pt/pt/docs/Portug_tax_system/Documents/Order_No_8632_2014_of_the_3rd_July.pdf
    #    """
    #    private_key_string = self._l10n_pt_get_private_key()
    #    private_key = serialization.load_pem_private_key(str.encode(private_key_string), password=None)
    #    signature = private_key.sign( message.encode(), padding.PKCS1v15(), hashes.SHA1())
    #    return base64.b64encode(signature).decode()

#
