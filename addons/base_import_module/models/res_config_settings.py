from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _get_x_industry_fields(self):
        """ Return the list of (field_name, module_name) for boolean fields whose
        name starts with `x_industry_`. Like `module_` fields, setting one of these
        to True and saving installs the corresponding module, except the module is
        fetched from the Odoo appstore instead of being looked up locally.

        The `x_industry_` prefix on a boolean `res.config.settings` field is
        reserved for this mechanism: any field named this way is assumed to
        name an appstore module to install, not a regular feature toggle.
        """
        return [
            (name, name.removeprefix('x_industry_'))
            for name, field in self._fields.items()
            if name.startswith('x_industry_') and field.type == 'boolean'
        ]

    @api.model
    def _get_x_module_fields(self):
        """ Return the list of (field_name, module_name) for fields whose name
        starts with `x_module_`. They behave like `module_` fields, for fields
        defined in data, whose names must start with `x_`.
        """
        x_module_fields = []
        for name, field in self._fields.items():
            if not name.startswith('x_module_'):
                continue
            if field.type != 'boolean':
                raise TypeError(f"Field {field} must have type 'boolean'")
            x_module_fields.append((name, name.removeprefix('x_module_')))
        return x_module_fields

    @api.model
    def get_values(self):
        res = super().get_values()
        IrModule = self.env['ir.module.module']
        for name, module_name in [*self._get_x_industry_fields(), *self._get_x_module_fields()]:
            module = IrModule._get(module_name)
            res[name] = module.state in ('installed', 'to install', 'to upgrade')
        return res

    def _get_modules_to_install(self, classified):
        to_install = super()._get_modules_to_install(classified)
        IrModule = self.env['ir.module.module']
        for from_appstore, fields in [
            (True, self._get_x_industry_fields()),
            (False, self._get_x_module_fields()),
        ]:
            for name, module_name in fields:
                if not self[name]:
                    continue
                module = IrModule._get(module_name)
                if module.state == 'installed':
                    continue
                to_install |= IrModule.new({'name': module_name}) if from_appstore and not module else module
        return to_install

    def _get_modules_to_uninstall(self, classified):
        to_uninstall = super()._get_modules_to_uninstall(classified)
        IrModule = self.env['ir.module.module']
        for name, module_name in [*self._get_x_industry_fields(), *self._get_x_module_fields()]:
            if self[name]:
                continue
            module = IrModule._get(module_name)
            if module.state in ('installed', 'to upgrade'):
                to_uninstall |= module
        return to_uninstall

    @api.model
    def _install_modules(self, modules):
        appstore_module_names = {module_name for _name, module_name in self._get_x_industry_fields()}
        to_install_appstore = modules.filtered(lambda m: m.name in appstore_module_names)

        result = super()._install_modules(modules - to_install_appstore)

        for module in to_install_appstore:
            self.env['ir.module.module']._install_data_module(module.name)

        return result
