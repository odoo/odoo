from odoo.http import Controller, request, route
from odoo.release import documentation_url


class Documentation(Controller):

    @route(
        ['/web/documentation', '/web/documentation/<path:target>'],
        type='http', auth='none', readonly=True, methods=['GET'],
    )
    def open(self, target=''):
        """
        Redirect to the odoo documentation corresponding to the version of the database.
        """
        return request.redirect(f'{documentation_url}/{target}', local=False)
