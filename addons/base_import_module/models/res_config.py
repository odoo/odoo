from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _get_appstore_fields(self, fnames=None):
        """ Return the list of (field_name, module_name) for boolean fields whose
        name starts with `x_module_`. Like `module_` fields, setting one of these
        to True and saving installs the corresponding module, except the module is
        fetched from the Odoo appstore instead of being looked up locally.
        """
        if fnames is None:
            fnames = self._fields.keys()

        appstore_fields = []
        for name in fnames:
            if name.startswith('x_module_'):
                field = self._fields[name]
                if field.type != 'boolean':
                    raise Exception("Field %s must have type 'boolean'" % field)
                appstore_fields.append((name, name[len('x_module_'):]))
        return appstore_fields

    @api.model
    def get_values(self):
        res = super().get_values()
        IrModule = self.env['ir.module.module']
        for name, module_name in self._get_appstore_fields():
            module = IrModule._get(module_name)
            res[name] = module.state in ('installed', 'to install', 'to upgrade')
        return res

    @api.model
    def _install_modules(self, modules):
        result = super()._install_modules(modules)

        IrModule = self.env['ir.module.module']
        for name, module_name in self._get_appstore_fields():
            if not self[name]:
                continue
            module = IrModule._get(module_name)
            if module.state == 'installed':
                continue
            IrModule._install_data_module(module_name)

        return result
