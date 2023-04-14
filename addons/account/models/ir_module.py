from importlib import import_module
from inspect import getmembers, ismodule, isclass, isfunction

from odoo import models, fields


def get_flag(country_code):
    # get the sequence of 2 regional indicator emoji forming the flag linked to the country code
    return "".join(chr(int(f"1f1{ord(c)+165:02x}", base=16)) for c in country_code)


class IrModule(models.Model):
    _inherit = "ir.module.module"

    account_templates = fields.Binary(compute='_compute_account_templates', exportable=False)

    def _get_template_data_function(self):
        self.ensure_one()

        chart_category = self.env.ref('base.module_category_accounting_localizations_account_charts')
        if self.category_id != chart_category and self.name != 'account':
            return

        try:
            loaded_module = import_module(f"odoo.addons.{self.name}.models")
        except ModuleNotFoundError:
            return

        def filter_template_module(m):
            return ismodule(m) and m.__name__.split('.')[-1].startswith('template_')
        def filter_template_data_function(f):
            return self.env['account.chart.template']._is_template_function(f) and f._l10n_template_key.model == 'template_data'

        for _mname, template_module in getmembers(loaded_module, filter_template_module):
            for _cname, template_class in getmembers(template_module, isclass):
                for _fname, template_data_function in getmembers(template_class, filter_template_data_function):
                    yield template_data_function

    def _compute_account_templates(self):
        for module in self:
            module.account_templates = {}
            for template_data_function in module._get_template_data_function():
                template_data = template_data_function(self.env['account.chart.template'])
                template_code = template_data_function._l10n_template_key.code
                template_name = template_data.get('name')
                template_country = template_data.get('country', '')
                country_code = template_country or template_country is not None and template_code.split('_')[0]
                country = country_code and self.env.ref(f"base.{country_code}", raise_if_not_found=False)
                country_name = f"{get_flag(country.code)} {country.name}" if country else ''
                description = country_name and (f"{country_name} - {template_name}" if template_name else country_name) or template_name

                module.account_templates[template_code] = {
                    'name': description,
                    'module': module.name,
                    'parent': template_data.get('parent'),
                    'country': country,
                    'country_id': country and country.id,
                    'country_code': country and country.code,
                    'visible': template_data.get('visible', True),
                }

    def write(self, vals):
        # Instanciate the first template of the module on the current company upon installing the module
        was_installed = len(self) == 1 and self.state in ('installed', 'to upgrade', 'to remove')
        super().write(vals)
        is_installed = len(self) == 1 and self.state == 'installed'
        if not was_installed and is_installed and not self.env.company.chart_template and self.account_templates:
            self.env.registry._auto_install_template = next(iter(self.account_templates))

    def _load_module_terms(self, modules, langs, overwrite=False):
        super()._load_module_terms(modules, langs, overwrite)
        if 'account' in modules:
            def load_account_translations(env):
                env['account.chart.template']._load_translations(langs=langs)
            if self.env.registry.loaded:
                load_account_translations(self.env)
            else:
                self.env.registry._delayed_account_translator = load_account_translations

    def _register_hook(self):
        super()._register_hook()
        if hasattr(self.env.registry, '_delayed_account_translator'):
            self.env.registry._delayed_account_translator(self.env)
            del self.env.registry._delayed_account_translator
        if hasattr(self.env.registry, '_auto_install_template'):
            self.env['account.chart.template'].try_loading(
                self.env.registry._auto_install_template,
                self.env.company,
            )
            del self.env.registry._auto_install_template
