from odoo.addons.web.controllers.home import Home


class InstagramHome(Home):

    def _get_allowed_robots_routes(self):
        """Sometimes Facebook crawler allowance is needed for it to properly download the image from our url."""
        return super()._get_allowed_robots_routes() + ['/social_instagram/']
