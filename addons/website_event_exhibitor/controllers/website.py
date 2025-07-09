from odoo.addons.website.controllers import main


class Website(main.Website):
    def _get_robots_directives(self):
        config = super()._get_robots_directives()

        disallow_patterns = [
            '/event/*/exhibitors?countries=',
            '/event/*/exhibitors?*&countries=',

            '/event/*/exhibitors?sponsorships=',
            '/event/*/exhibitors?*&sponsorships=',
        ]

        config['*']['disallow'].extend(disallow_patterns)

        return config
