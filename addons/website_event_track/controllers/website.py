from odoo.addons.website.controllers import main


class Website(main.Website):
    def _get_robots_directives(self):
        config = super()._get_robots_directives()

        disallow_patterns = [
            '/event/*/track?tags=',
            '/event/*/track?*&tags=',
        ]

        config['*']['disallow'].extend(disallow_patterns)

        return config
