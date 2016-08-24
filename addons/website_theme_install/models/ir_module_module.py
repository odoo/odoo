import os
from openerp import api, fields, models, _

class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _inherit = _name

    image_ids = fields.One2many('ir.attachment', 'res_id',
                                domain=[('res_model', '=', _name), ('mimetype', '=like', 'image/%')],
                                string='Screenshots', readonly=True)

    @api.model
    def update_list(self):
        res = super(IrModuleModule, self).update_list()

        IrAttachment = self.env['ir.attachment']
        existing_urls = IrAttachment.search_read([['res_model', '=', self._name], ['type', '=', 'url']], ['url'])
        existing_urls = [url_wrapped['url'] for url_wrapped in existing_urls]

        for app in self.search([]):
            terp = self.get_module_info(app.name)
            images = terp.get('images', [])
            for image in images:
                image_path = os.path.join(app.name, image)
                if image_path not in existing_urls:
                    image_name = os.path.basename(image_path)
                    IrAttachment.create({
                        'type': 'url',
                        'name': image_name,
                        'datas_fname': image_name,
                        'url': image_path,
                        'res_model': self._name,
                        'res_id': app.id,
                    })

        return res

    @api.multi
    def button_choose_theme(self):
        theme_category_id = self.env.ref('base.module_category_theme').id
        self.search([ # Uninstall the theme(s) which is (are) installed
            ('state', '=', 'installed'),
            '|', ('category_id', 'not in', [self.env.ref('base.module_category_hidden').id, self.env.ref('base.module_category_theme_hidden').id]), ('name', '=', 'theme_default'),
            '|', ('category_id', '=', theme_category_id), ('category_id.parent_id', '=', theme_category_id)
        ]).button_immediate_uninstall()

        next_action = self.button_immediate_install() # Then install the new chosen one
        if next_action.get('tag') == 'reload' and not next_action.get('params', {}).get('menu_id'):
            next_action = self.env.ref('website.action_website_tutorial').read()[0]

        return next_action
