# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.tools import format_list
from odoo.exceptions import AccessError


class ProjectSharingMixin(models.AbstractModel):
    _name = 'project.sharing.mixin'
    _description = 'Project Sharing Mixin'

    @property
    def SELF_READABLE_FIELDS(self) -> set[str]:
        return {'id', 'display_name'} | self.SELF_WRITABLE_FIELDS

    @property
    def SELF_WRITABLE_FIELDS(self) -> set[str]:
        return set()

    def _ensure_fields_are_accessible(self, fields: list, write_operation: bool = False) -> None:
        """" ensure all fields are accessible by the current user

            This method checks if the portal user can access to all fields given in parameter.

            :param fields: list of fields to check if the current user can access.
            :param operation: contains either 'read' to check readable fields or 'write' to check writable fields.
        """
        if fields and not self.env.su:
            unauthorized_fields = set(fields) - (self.SELF_WRITABLE_FIELDS if write_operation else self.SELF_READABLE_FIELDS)
            if unauthorized_fields:
                unauthorized_field_list = format_list(self.env, list(unauthorized_fields))
                if write_operation:
                    error_message = _('You cannot write on the following fields on %(model_name)s: %(field_list)s', model_name=self._name, field_list=unauthorized_field_list)
                else:
                    error_message = _('You cannot read the following fields on %(model_name)s: %(field_list)s', model_name=self._name, field_list=unauthorized_field_list)
                raise AccessError(error_message)

    def _ensure_specification_is_accessible(self, specification: dict[str, dict], write_operation: bool = False) -> None:
        """ ensure fields defined in specification to read/write accessible by the current user

            This method checks if the portal user can access to all fields given in the specification parameter.
        """
        self._ensure_fields_are_accessible(specification.keys(), write_operation)
        for field_name, field_spec in specification.items():
            field = self._fields[field_name]
            if field.type in ('many2one', 'one2many', 'many2many') and field_spec:
                if 'fields' not in field_spec:
                    continue
                CoModel = self.env[field.comodel_name]
                if hasattr(CoModel, '_ensure_fields_are_accessible'):
                    CoModel._ensure_fields_are_accessible(field_spec['fields'], write_operation)
                else:
                    error_message = None
                    if write_operation:
                        error_message = _('You cannot write on the %(co_model_name)s', co_model_name=field.comodel_name)
                    else:
                        authorized_fields = {'id', 'display_name'}
                        unauthorized_fields = set(field_spec['fields']) - authorized_fields
                        if unauthorized_fields:
                            unauthorized_field_list = format_list(self.env, list(unauthorized_fields))
                            error_message = _('You cannot read the following fields on %(co_model_name)s: %(field_list)s', co_model_name=field.comodel_name, field_list=unauthorized_field_list)
                    if error_message:
                        raise AccessError(error_message)

    @api.model
    @api.readonly
    def project_sharing_get_views(self, views: list[tuple[int, str]], options: dict | None = None) -> dict[str, dict]:
        result = self.get_views(views, options)
        fields = result['models']['project.task']['fields']
        readable_fields = self.SELF_READABLE_FIELDS
        public_fields = {field_name: description for field_name, description in fields.items() if field_name in readable_fields}
        writable_fields = self.SELF_WRITABLE_FIELDS
        for field_name, description in public_fields.items():
            if field_name not in writable_fields and not description.get('readonly', False):
                description['readonly'] = True
        result['models']['project.task']['fields'] = public_fields
        return result

    @api.model
    @api.readonly
    def project_sharing_name_search(self, name='', args=None, operator='ilike', limit=100):
        fields_to_check = {leaf[0] for leaf in args or [] if isinstance(leaf, (list, tuple))}
        fields_to_check.add('name')
        self._ensure_fields_are_accessible(fields_to_check)
        return self.name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    @api.readonly
    def project_sharing_web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, lazy=True):
        fields_to_check = [leaf[0] for leaf in domain if isinstance(leaf, (list, tuple))]
        self._ensure_fields_are_accessible(fields_to_check)
        return self.web_read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    @api.readonly
    def project_sharing_read_progress_bar(self, domain, group_by, progress_bar):
        fields_to_check = [leaf[0] for leaf in domain if isinstance(leaf, (list, tuple))]
        fields_to_check.extend([group_by, progress_bar['field']])
        self._ensure_fields_are_accessible(fields_to_check)
        return self.read_progress_bar(domain, group_by, progress_bar)

    @api.model
    @api.readonly
    def project_sharing_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs) -> list[dict]:
        fields_to_check = {leaf[0] for leaf in domain or [] if isinstance(leaf, (list, tuple))}
        fields_to_check.update(fields or [])
        self._ensure_fields_are_accessible(fields_to_check)
        return self.search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)

    @api.model
    @api.readonly
    def project_sharing_web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None) -> list[dict]:
        fields_to_check = [leaf[0] for leaf in domain if isinstance(leaf, (list, tuple))]
        self._ensure_fields_are_accessible(fields_to_check)
        self._ensure_specification_is_accessible(specification)
        return self.web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)

    @api.readonly
    def project_sharing_web_read(self, specification: dict[str, dict]) -> list[dict]:
        self._ensure_specification_is_accessible(specification)
        return self.web_read(specification)

    def project_sharing_onchange(self, values: dict, field_names: list[str], fields_spec: dict) -> dict:
        self._ensure_fields_are_accessible(set(values.keys()).union(field_names))
        self._ensure_specification_is_accessible(fields_spec)
        return self.onchange(values, field_names, fields_spec)

    def project_sharing_web_save(self, vals, specification: dict[str, dict], next_id: int | bool = False) -> list[dict]:
        if self:
            self.project_sharing_write(vals)
        else:
            self = self.project_sharing_create(vals)
        if next_id:
            self = self.browse(next_id)
        return self.with_context(bin_size=True).project_sharing_web_read(specification)
