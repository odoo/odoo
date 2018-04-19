# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from hashlib import sha256
from json import dumps


class UnalterableFieldsMixin(models.AbstractModel):
    ''' Mixin used to make all or certain fields unalterable on record under conditions. '''
    _name = 'unalterable.fields.mixin'

    @api.model
    def _get_unalterable_fields(self):
        ''' Get the fields considered as unalterable.
        If this method returns None, it means all fields are considered as unalterable.

        :return: None or a list of field name.
        '''
        return None

    @api.multi
    def _is_object_unalterable(self):
        ''' Determine when a record move to 'unalterable' mode.
        No need to override this method if the record must be unalterable directly.

        :return: True if the record becomes unalterable, False otherwise.
        '''
        return True

    # ============
    # MAIN METHODS
    # ============

    @api.multi
    def write(self, vals):
        # Check fields inalterability.
        if any(r._is_object_unalterable() for r in self):
            unalterable_fields = self._get_unalterable_fields()
            if unalterable_fields is None or set(vals).intersection(unalterable_fields):
                raise UserError(_('Editing an unalterable record is prohibited to stay compliant with the law applied to your company.'))
        return super(UnalterableFieldsMixin, self).write(vals)

    @api.multi
    def unlink(self):
        # Check records inalterability.
        if any(r._is_object_unalterable() for r in self):
            raise UserError(_('An unalterable record can\'t be unlinked.'))
        return super(UnalterableFieldsMixin, self).unlink()


class UnalterableHashMixin(models.AbstractModel):
    '''
    Override of the unalterable.fields.mixin.

    Add an hashing mechanism to preserve the data integrity in a hash history. Indeed, the hash is computed based
    on unalterable fields plus the previous hashed record in the history.
    This mechanism guarantees the data remains in their original state when the hash was done.

    unalterable_sequence_number is the sequence number of the record in the hash history.
    unalterable_hash is the hash computed using the hash of the previous record and the unalterable fields.
    '''
    _name = 'unalterable.hash.mixin'
    _inherit = 'unalterable.fields.mixin'

    unalterable_sequence_number = fields.Integer(string='Unalterable Sequence #', readonly=True, copy=False)
    unalterable_hash = fields.Char(string='Unalterable Hash', readonly=True, copy=False)

    @api.model
    def _get_company_field_name(self):
        ''' Get the field name corresponding to the company owning the record.
        By default, the inalterability mixin looks for the 'company_id' field.
        Note: Composite fields are allowed: e.g journal_id.company_id.
        Note2: Returning None means the record is not on any company.

        :return: The field name or path linking the record to a company.
        '''
        return 'company_id' if 'company_id' in self._fields else None

    @api.model
    def _get_unalterable_model_sequence_code(self):
        ''' If a sequence doesn't exist yet for this kind of records, create a new one.
        This method create a new sequence code based on the model name.

        :return: A sequence code.
        '''
        prefix = self._name.replace('.', '').upper()
        return '%s_UNALTERABLE' % prefix

    @api.multi
    def _get_create_unalterable_sequence(self):
        ''' Get the sequence to create the history.
        If not found, the sequence is automatically created.

        :return: An ir.sequence record.
        '''
        self.ensure_one()

        sequence_code = self._get_unalterable_model_sequence_code()
        domain = [('code', '=', sequence_code)]
        company_field = self._get_company_field_name()
        company = company_field and self.mapped(company_field)[0]
        if company:
            domain.append(('company_id', '=', company.id))

        # Search an existing sequence.
        sequence = self.env['ir.sequence'].search(domain, limit=1)

        if sequence:
            return sequence

        # Create a new sequence.
        sequence = self.env['ir.sequence'].sudo().create({
            'name': 'Unalterable Accounting Sequence for %s' % self._name,
            'code': sequence_code,
            'implementation': 'no_gap',
            'company_id': company and company.id,
        })

        # Create a server action to check the inalterability of records in tree view.
        server_action = self.env['ir.actions.server'].sudo().create({
            'id': 'action_check_hash_integrity_%s' % self._name,
            'name': 'Check hash integrity of %s records' % self._name,
            'model_id': self.env['ir.model']._get(self._name).id,
            'type': 'ir.actions.server',
            'state': 'code',
            'code': "action = env['%s']._check_hash_integrity()" % self._name,
        })
        server_action.create_action()

        return sequence

    @api.multi
    def _get_previous_unalterable_object(self, previous_sequence_number):
        ''' Get the previous record on the hash history.

        :return: The previous record.
        '''
        self.ensure_one()
        domain = [('unalterable_sequence_number', '=', previous_sequence_number)]
        company_field = self._get_company_field_name()
        company = company_field and self.mapped(company_field)[0]
        if company:
            domain.append(('company_id', '=', company.id))
        return self.env[self._name].search(domain, limit=1)

    @api.multi
    def _get_unalterable_hash(self):
        ''' Create and return a new hash for the record.

        :return: A sha256 hash.
        '''
        self.ensure_one()

        # Compute hash string for current record.
        unalterable_fields = self._get_unalterable_fields()
        if unalterable_fields is None:
            dict_values = self.read()[0]
        else:
            dict_values = {}
            for field_name in unalterable_fields:
                if field_name not in self:
                    raise UserError(_('%s field name doesn\'t exist in %s model.') % (field_name, self._name))

                field_type = self._fields[field_name].type
                field_value = self[field_name]
                if field_type == 'many2one':
                    dict_values[field_name] = field_value.id
                elif field_type in ('many2many', 'one2many'):
                    dict_values[field_name] = [r.id for r in sorted(field_value, key=lambda r: r.id)]
                else:
                    dict_values[field_name] = field_value
        hash_string = dumps(dict_values, sort_keys=True, ensure_ascii=True, indent=None, separators=(',', ':'))

        # Retrieve hash from previous record.
        if self.unalterable_sequence_number > 1:
            previous_record = self._get_previous_unalterable_object(self.unalterable_sequence_number - 1)
            previous_hash = previous_record and previous_record.unalterable_hash
        else:
            previous_hash = None

        hash_string_utf8 = ((previous_hash or u'') + hash_string).encode('utf-8')
        return sha256(hash_string_utf8).hexdigest()

    @api.multi
    def _compute_unalterable_hash(self):
        ''' Compute the hash in a batch records. '''
        for record in self:
            if record.unalterable_sequence_number or record.unalterable_hash:
                raise UserError(_('A hash sequence already exist for record.'))

            # Compute the sequence.
            hash_sequence = record._get_create_unalterable_sequence()
            super(UnalterableHashMixin, record).write({'unalterable_sequence_number': int(hash_sequence.next_by_id())})

            # Compute the hash.
            super(UnalterableHashMixin, record).write({'unalterable_hash': record._get_unalterable_hash()})

    @api.model
    def _check_hash_integrity(self):
        ''' Check the hash of all records and raise an error if a corrupted data is found.
        In case of success, raise an error too... but a great error this time!
        '''
        domain = [('unalterable_sequence_number', '!=', 0)]
        company_field = self._get_company_field_name()
        if company_field:
            company = self.env.user.company_id
            domain.append((company_field, '=', company.id))
        if self._context.get('active_ids'):
            domain.append(('id', 'in', self._context['active_ids']))

        records = self.env[self._name].search(domain)

        for record in records:
            if record.unalterable_hash != record._get_unalterable_hash():
                raise UserError(_('Corrupted data found on %s with id: %d.') % (record._description, record.id))

        raise UserError(_('Successful test! These data are guaranteed to be in their original and inalterable state.'))

    @api.model
    def create(self, vals):
        # If a record is directly inalterable, compute the hash directly.
        res = super(UnalterableHashMixin, self).create(vals)
        if res._is_object_unalterable():
            res._compute_unalterable_hash()
        return res

    @api.multi
    def write(self, vals):
        # Check bypassing the inalterability by setting hash fields explicitly.
        if vals.get('unalterable_sequence_number') or vals.get('unalterable_hash'):
            raise UserError(_('The fields unalterable_sequence_number/unalterable_hash are not editable manually.'))

        res = super(UnalterableHashMixin, self).write(vals)

        # Compute hash on newly unalterable records.
        not_hashed_records = self.filtered(lambda r: r._is_object_unalterable() and not r.unalterable_hash)
        not_hashed_records._compute_unalterable_hash()

        return res
