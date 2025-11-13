from importlib import import_module
from inspect import getmembers, ismodule, isclass, isfunction

from odoo import api, models, fields
from odoo.tools.misc import get_flag


def templ(env, code2country, name=None, country_code='', **kwargs):
    country = country_code and code2country.get(country_code.upper())
    country_name = f"{get_flag(country.code)} {country.name}" if country else ''
    return {
        'name': country_name and (f"{country_name} - {name}" if name else country_name) or name,
        'country_id': country and country.id,
        **kwargs,
    }

template_module = lambda m: ismodule(m) and m.__name__.split('.')[-1].startswith('template_')
template_class = isclass
template_function = lambda f: isfunction(f) and hasattr(f, '_l10n_template') and f._l10n_template[1] == 'template_data'

TEMPLATE_REGISTER = {}


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    account_templates = fields.Binary(compute='_compute_account_templates', exportable=False)

    @api.depends('state')
    def _compute_account_templates(self):
        code2country = self.env['res.country'].search([]).grouped('code')
        for module in self:
            module.account_templates = {
                code: templ(self.env, code2country, **vals)
                for code, vals in module._get_module_template().items()
            }

    def _get_module_template(self):
        if self.name not in TEMPLATE_REGISTER:
            chart_category = self.env.ref('base.module_category_accounting_localizations_account_charts')
            templates = {}
            if self.category_id == chart_category or self.name == 'account':
                try:
                    python_module = import_module(f"odoo.addons.{self.name}.models")
                except ModuleNotFoundError:
                    pass
                else:
                    for _name, mdl in getmembers(python_module, template_module):
                        for _name, cls in getmembers(mdl, template_class):
                            for _name, fct in getmembers(cls, template_function):
                                if (template_values := fct(self.env['account.chart.template'])):
                                    code = fct._l10n_template[0]
                                    country = template_values.get('country', '')
                                    country_code = country or code.split('_')[0] if country is not None else None
                                    templates[code] = {
                                        'name': template_values.get('name'),
                                        'parent': template_values.get('parent'),
                                        'sequence': template_values.get('sequence', 1),
                                        'country': country,
                                        'country_code': country_code,
                                        'visible': template_values.get('visible', True),
                                        'module': self.name,
                                    }
            TEMPLATE_REGISTER[self.name] = dict(sorted(templates.items(), key=lambda kv: kv[1]['sequence']))
        return TEMPLATE_REGISTER[self.name]

    def write(self, vals):
        # Instanciate the first template of the module on the current company upon installing the module
        was_installed = len(self) == 1 and self.state in ('installed', 'to upgrade', 'to remove')
        res = super().write(vals)
        is_installed = len(self) == 1 and self.state == 'installed'
        if not was_installed and is_installed:
            if self.name != 'account':
                for demo in [False, True] if self.demo else [False]:
                    for company in self.env['res.company'].search([('chart_template', '!=', False)]):
                        ChartTemplate = self.env['account.chart.template'].with_company(company)
                        module_template_data = ChartTemplate._get_chart_template_data(company.chart_template, demo, self.name)
                        module_template_data.pop('template_data', None)
                        if module_template_data:
                            ChartTemplate._pre_reload_data(company, {}, module_template_data, force_update=True)
                            ChartTemplate._load_data(module_template_data)
            if (
                not self.env.company.chart_template
                and self.account_templates
                and (guessed := next((
                    tname
                    for tname, tvals in self.account_templates.items()
                    if (self.env.company.country_id.id and tvals['country_id'] == self.env.company.country_id.id)
                    or tname == 'generic_coa'
                ), None))
            ):
                def try_loading(env):
                    env['account.chart.template'].try_loading(
                        guessed,
                        env.company,
                    )
                self.env.registry._auto_install_template = try_loading
        return res

    def _load_module_terms(self, modules, langs, overwrite=False):
        super()._load_module_terms(modules, langs, overwrite=overwrite)
        if 'account' in modules:
            def load_account_translations(env):
                env['account.chart.template']._load_translations(langs=langs)
                env['account.account.tag']._translate_tax_tags(langs=langs)
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
            self.env.registry._auto_install_template(self.env)
            del self.env.registry._auto_install_template

    def module_uninstall(self):
        unlinked_templates = [code for template in self.mapped('account_templates') for code in template]
        if unlinked_templates:
            companies = self.env['res.company'].search([
                ('chart_template', 'in', unlinked_templates),
            ])
            companies.chart_template = False
            companies.flush_recordset()

        return super().module_uninstall()
