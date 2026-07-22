from odoo import api, models

MENU_NAME_OVERRIDES = {
    'contacts.menu_contacts': "Clientes",
    'sale.sale_menu_root': "Preventas",
}


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _distribuidora_config_apply_menu_names(self):
        # name es un campo traducible (jsonb por idioma); escribirlo sin
        # contexto de idioma solo toca el idioma de referencia (en_US), no
        # el idioma que realmente usan los usuarios (es_CR). Por eso se
        # recorre cada idioma instalado y se escribe explicitamente.
        installed_langs = [code for code, _name in self.env['res.lang'].get_installed()]
        for xmlid, name in MENU_NAME_OVERRIDES.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            for lang in installed_langs:
                menu.with_context(lang=lang).name = name
