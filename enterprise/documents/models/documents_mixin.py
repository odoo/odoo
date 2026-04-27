# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models


class DocumentMixin(models.AbstractModel):
    """
    Inherit this mixin to automatically create a `documents.document` when
    an `ir.attachment` is linked to a record and add the default values when
    creating a document related to the model that inherits from this mixin.

    Override this mixin's methods to specify an owner, a folder, tags or
    access_rights for the document.

    Note: this mixin can be disabled with the context variable "no_document=True".
    """
    _name = 'documents.mixin'
    _inherit = 'documents.unlink.mixin'
    _description = "Documents creation mixin"

    def _get_document_vals(self, attachment):
        """
        Return values used to create a `documents.document`
        """
        self.ensure_one()
        document_vals = {}
        if self._check_create_documents():
            access_rights_vals = self._get_document_vals_access_rights()
            if set(access_rights_vals) - {'access_via_link', 'access_internal', 'is_access_via_link_hidden'}:
                raise ValueError("Invalid access right values")
            folder = self._get_document_folder()
            document_vals = {
                'attachment_id': attachment.id,
                'name': attachment.name or self.display_name,
                'folder_id': folder.id,
                'company_id': folder.company_id.id,
                'owner_id': self._get_document_owner().id,
                'partner_id': self._get_document_partner().id,
                'tag_ids': [(6, 0, self._get_document_tags().ids)],
            } | access_rights_vals
        return document_vals

    def _get_document_vals_access_rights(self):
        """ Return access rights values to create a `documents.document`

        In the default implementation, we give the minimal permission and rely on the propagation of the folder
        permission but this method can be overridden to set more open rights.

        Authorized fields: access_via_link, access_internal, is_access_via_link_hidden.
        Note: access_ids are handled differently because when set, it prevents inheritance from the parent folder
        (see specific document override).
        """
        return {
            'access_via_link': 'none',
            'access_internal': 'none',
            'is_access_via_link_hidden': True,
        }

    def _get_document_owner(self):
        """ Return the owner value to create a `documents.document`

        In the default implementation, we return OdooBot as owner to avoid giving full access to a user and to rely
        instead on explicit access managed via `document.access` or via parent folder access inheritance but this
        method can be overridden to for example give the ownership to the current user.
        """
        return self.env.ref('base.user_root')

    def _get_document_tags(self):
        return self.env['documents.tag']

    def _get_document_folder(self):
        return self.env['documents.document']

    def _get_document_partner(self):
        return self.env['res.partner']

    def _get_document_access_ids(self):
        """ Add or remove members

        :return boolean|list: list of tuple (partner, (role, expiration_date)) or False to avoid
        inheriting members from parent folder.
        """
        return []

    def _check_create_documents(self):
        return bool(self and self._get_document_folder())

    def _prepare_document_create_values_for_linked_records(
            self, res_model, vals_list, pre_vals_list):
        """ Set default value defined on the document mixin implementation of the related record if there are not
        explicitly set.

        :param str res_model: model referenced by the documents to consider
        :param list[dict] vals_list: list of values
        :param list[dict] pre_vals_list: list of values before _prepare_create_values (no permission inherited yet)

        Note:
        - This method doesn't override existing values (permission, owner, ...).
        - The related record res_model must inherit from DocumentMixin
        """
        if self._name != res_model:
            raise ValueError(f'Invalid model {res_model} (expected {self._name})')

        related_record_by_id = self.env[res_model].browse([
            res_id for vals in vals_list if (res_id := vals.get('res_id'))]).grouped('id')
        for vals, pre_vals in zip(vals_list, pre_vals_list):
            if not vals.get('res_id'):
                continue
            related_record = related_record_by_id.get(vals['res_id'])
            vals.update(
                {
                    'owner_id': pre_vals.get('owner_id', related_record._get_document_owner().id),
                    'partner_id': pre_vals.get('partner_id', related_record._get_document_partner().id),
                    'tag_ids': pre_vals.get('tag_ids', [(6, 0, related_record._get_document_tags().ids)]),
                } | {
                    key: value
                    for key, value in related_record._get_document_vals_access_rights().items()
                    if key not in pre_vals
                })
            if 'access_ids' in pre_vals:
                continue
            access_ids = vals.get('access_ids') or []
            partner_with_access = {access[2]['partner_id'] for access in access_ids if access[2]}  # list of Command.create tuples
            related_document_access = related_record._get_document_access_ids()
            if related_document_access is False:
                # Keep logs but remove members
                access_ids = [a for a in access_ids if a[2] and not a[2].get('role')]
            else:
                accesses_to_add = [
                    (partner, access)
                    for partner, access in related_record._get_document_access_ids()
                    if partner.id not in partner_with_access
                ]
                if accesses_to_add:
                    access_ids.extend(
                        Command.create({
                            'partner_id': partner.id,
                            'role': role,
                            'expiration_date': expiration_date,
                        })
                        for partner, (role, expiration_date) in accesses_to_add
                    )
            vals['access_ids'] = access_ids
        return vals_list
