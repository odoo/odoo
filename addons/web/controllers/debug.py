from odoo.http import Controller, request, route


class Debug(Controller):

    @route('/web/profiling', type='json', auth='public', sitemap=False)
    def profile(self, **kwargs):
        return request.env['ir.profile.session']._update_profiling(**kwargs)
