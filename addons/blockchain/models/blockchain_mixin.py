import operator
from hashlib import sha256
from json import dumps

from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools import float_repr


class BlockchainMixin(models.AbstractModel):
    """
    This mixin can be inherited by models that need a blockchaining system.
    The flow is as follows:
    1. The user activates the restrict mode on the parent record (e.g. account.journal)
    2. A secure sequence is created on the parent record (e.g. account.journal)
    3. The user creates a new record (e.g. account.move)
    4. _compute_blockchain_must_hash will be called when any of its dependencies is modified (e.g. the state of the account.move)
    5. The blockchain_must_hash field will be set to True if the record must be hashed (e.g. the account.move is posted and its journal is in restrict mode)
    6. The _compute_blockchain_secure_sequence_number method will be called when the blockchain_must_hash field is updated to True
    7. The blockchain_secure_sequence_number field will be set to the next number of the secure sequence of the parent record (e.g. account.journal)
    8. The _compute_blockchain_inalterable_hash method will be called when the blockchain_secure_sequence_number field is updated
    9. If the blockchain_inalterable_hash field is not set yet, it will be by calling the _get_blockchain_record_hash_string method
    10. The _get_blockchain_record_hash_string method will compute the hash of the current record using:
        - the hash of the previous record in the secure sequence chain
        - the fields defined in _get_blockchain_inalterable_hash_fields
    11. If the blockchain_inalterable_hash, the blockchain_secure_sequence_number or any of the fields defined in _get_blockchain_inalterable_hash_fields is modified, an error will be raised
    """
    _name = 'blockchain.mixin'
    _description = "Blockchain Mixin"

    blockchain_must_hash = fields.Boolean(compute='_compute_blockchain_must_hash')
    blockchain_secure_sequence_number = fields.Integer(
        string='Inalterable no-gap sequence number',
        compute='_compute_blockchain_secure_sequence_number', store=True, readonly=True,
        copy=False
    )
    blockchain_inalterable_hash = fields.Char(
        string='Inalterable hash',
        compute='_compute_blockchain_inalterable_hash', store=True, readonly=True,
        copy=False
    )

    def _get_blockchain_secure_sequence(self):
        """
        This method must be overriden by the inheriting class.
        Get the sequence object used to build the hash chain.
        :returns: the linked sequence
        :rtype: Model<ir.sequence>
        E.g.: account.move is a link (i.e. has a blockchain_secure_sequence_number) in the
        chain of account.journal (i.e. has a secure_sequence).
        """
        raise NotImplementedError("'_get_blockchain_secure_sequence' must be overriden by the inheriting class")

    def _compute_blockchain_must_hash(self):
        """
        This method must be overriden by the inheriting class.
        :returns: True if the record must be hashed (depending on some record fields), False otherwise
        """

    def _get_blockchain_sorting_keys(self):
        """
        This method must be overriden by the inheriting class.
        :returns: the keys on which the records will be sorted
        :rtype: List[str]
        E.g.: ['invoice_date', 'amount_total']
        """
        raise NotImplementedError("'_get_blockchain_sorting_keys' must be overriden by the inheriting class")

    def _get_blockchain_previous_record_domain(self):
        """
        This method must be overriden by the inheriting class.
        :returns: the Odoo domain used to find the previous record in the secure sequence chain
        :rtype: Odoo domain (List[Tuple[str]])
        """
        raise NotImplementedError("'_get_blockchain_previous_record_domain' must be overriden by the inheriting class")

    def _get_blockchain_inalterable_hash_fields(self):
        """
        This method must be overriden by the inheriting class.
        :returns: the list of fields used to compute the hash
        :rtype: List[str]
        This means that once the inalterable hash is computed, we will no longer be able to modify these fields
        (otherwise the newly computed hash would be different)
        E.g.: ('create_date', 'done_date', 'name')
        """
        raise NotImplementedError("'_get_blockchain_inalterable_hash_fields' must be overriden by the inheriting class")

    @api.model
    def _get_blockchain_max_version(self):
        """
        If multiple versions of the hash algorithm are implemented, this method must be overriden by the inheriting class.
        :returns: the maximum version of the hash algorithm
        """
        return 3  # see why in _get_field_as_string

    @api.depends('blockchain_must_hash')
    def _compute_blockchain_secure_sequence_number(self):
        records = self.filtered(lambda r: r.blockchain_must_hash and not r.blockchain_secure_sequence_number)
        if not records:
            return
        for record in records._sort_blockchain_records():
            record.blockchain_secure_sequence_number = record._get_blockchain_secure_sequence().next_by_id()

    @api.model
    def _sort_blockchain_records(self):
        """
        :returns: the records sorted by the keys defined in _get_blockchain_sorting_keys
        :rtype: List[Model<blockchain.mixin>]
        """
        return self.sorted(key=operator.attrgetter(*self._get_blockchain_sorting_keys()))

    @api.model
    def _create_blockchain_secure_sequence(self, records, sequence_field_name, company_id):
        """Create a secure no_gap sequence on the given records"""
        for record in records:
            if record[sequence_field_name]:
                continue
            seq = self.env['ir.sequence'].create({
                'name': _('Securisation of %s - %s') % (record.id, sequence_field_name),
                'code': 'SECUR%s-%s' % (record.id, sequence_field_name),
                'implementation': 'no_gap',
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'company_id': 'company_id' in record and record.company_id.id or company_id,
            })
            record.write({sequence_field_name: seq.id})

    @api.depends('blockchain_secure_sequence_number')
    def _compute_blockchain_inalterable_hash(self):
        for record in self.sorted("blockchain_secure_sequence_number"):
            if not record.blockchain_inalterable_hash and record.blockchain_must_hash:
                record.blockchain_inalterable_hash = record._get_blockchain_record_hash_string()
                record.flush_recordset()  # Make sure the hash is stored in the database before computing the next one (which depends on this one)

    def _get_blockchain_record_hash_string(self, previous_hash=None):
        """
        :param previous_hash: the hash of the previous record in the secure sequence chain
        :returns: the hash computed using the previous hash and the fields defined in _get_blockchain_inalterable_hash_fields
        :rtype: str
        """
        self.ensure_one()
        # Make the json serialization canonical https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
        hash_string = dumps(
            self._get_blockchain_record_dict_to_hash(),
            sort_keys=True, ensure_ascii=True,
            indent=None, separators=(',', ':')
        )
        previous_hash = previous_hash or self._get_blockchain_record_previous_hash()
        hash_string = sha256((previous_hash + hash_string).encode('utf-8'))
        return hash_string.hexdigest()

    def _get_blockchain_record_previous_hash(self):
        """
        :returns: the hash of the previous record in the secure_sequence chain, or '' if it is the first record.
        """
        self.ensure_one()
        query_obj = self._search(domain=self._get_blockchain_previous_record_domain(), limit=1, order='blockchain_secure_sequence_number DESC')
        query_str, query_params = query_obj.select('blockchain_inalterable_hash')
        self._cr.execute(query_str, query_params)
        res = self._cr.fetchone()
        if not res or not res[0]:
            return ''
        return res[0]

    def _get_blockchain_record_dict_to_hash(self, lines=()):
        """
        :param lines: recordset of models which must inherit from sub.blockchain.mixin
        :returns: a dictionary (containing the fields to be hashed and their values) that will be hashed
        :rtype: dict
        See example in test_account_move_get_blockchain_record_dict_to_hash
        """
        self.ensure_one()
        result = {}
        for field in self._get_blockchain_inalterable_hash_fields():
            result[field] = self._get_field_as_string(self, field)

        for line in lines:
            for field in line._get_sub_blockchain_inalterable_hash_fields():
                k = 'line_%d_%s' % (line.id, field)
                result[k] = self._get_field_as_string(line, field)
        return result

    @api.model
    def _get_field_as_string(self, obj, field_str):
        field_value = obj[field_str]
        if obj._fields[field_str].type == 'many2one':
            field_value = field_value.id
        if obj._fields[field_str].type in ['many2many', 'one2many']:
            field_value = field_value.sorted().ids
        if obj._fields[field_str].type == 'monetary' and self._get_blockchain_max_version() >= 3:
            return float_repr(field_value, obj.currency_id.decimal_places)
        return str(field_value)

    def write(self, vals):
        for record in self:
            if record.blockchain_inalterable_hash:
                inalterable_fields = set(record._get_blockchain_inalterable_hash_fields()).union({'blockchain_inalterable_hash', 'blockchain_secure_sequence_number'})
                violated_fields = ", ".join([
                    record._fields[violated_field].string
                    for violated_field
                    in set(vals).intersection(inalterable_fields)
                ])
                if violated_fields:
                    raise UserError(_("You cannot edit the following fields due to restrict mode being activated: %s.", violated_fields))
        return super().write(vals)


class SubBlockchainMixin(models.AbstractModel):
    """
    This mixin is used for models which are themselves used in another model which is hashed.
    In such case, the base model must inherit from BlockchainMixin and the sub-models must inherit from SubBlockchainMixin.
    For instance, if we want account.move to use blockchain.mixin, and we want to use some fields of account.move.line in
    the hash of account.move, then account.move.line must inherit from sub.blockchain.mixin and implement the following methods.
    This allows us to verify that, if the parent model is hashed, then the fields returned by _get_sub_blockchain_inalterable_hash_fields()
    cannot be modified.
    """
    _name = 'sub.blockchain.mixin'
    _description = "Sub Blockchain Mixin"

    def _get_sub_blockchain_parent(self):
        """
        This method must be overriden by the inheriting class.
        :returns: the parent model which is hashed
        :rtype: Model<blockchain.mixin>
        E.g.: account.move.line will return its move_id corresponding to an account.move
        """
        raise NotImplementedError("'_get_sub_blockchain_parent' must be overriden by the inheriting class")

    def _get_sub_blockchain_inalterable_hash_fields(self):
        """
        This method must be overriden by the inheriting class.
        :returns: a tuple of fields which are used to compute the hash of the parent model
        in `BlockchainMixin._get_blockchain_record_dict_to_hash`
        E.g.: ('create_date', 'debit', 'done_date')
        """
        return ()

    def write(self, vals):
        for record in self:
            violated_fields = set(vals).intersection(record._get_sub_blockchain_inalterable_hash_fields())
            if violated_fields and record._get_sub_blockchain_parent().blockchain_inalterable_hash:
                violated_fields = ", ".join([record._fields[violated_field].string for violated_field in violated_fields])
                raise UserError(_("You cannot edit the following fields due to restrict mode being activated: %s.", violated_fields))
        return super().write(vals)
