from odoo.addons.website.controllers import form


class WebsiteForm(form.WebsiteForm):
    _input_filters = {
        **form.WebsiteForm._input_filters,
        'one2many_skill': form.WebsiteForm.one2many,
    }
