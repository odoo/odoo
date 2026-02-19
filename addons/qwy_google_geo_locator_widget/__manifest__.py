{
    "name": "Geo locator Widget",
    "description": """The Geo locator widget app provides the address input functionality to the users by integrating 
                      Google Maps through Google API Integration.""",
    "summary": "The City Geo locator app enables users to easily input city by integrating Google Maps through the "
               "Google API. It allows users to enter an city, automatically display the locations matching the user "
               "input, and auto-populate lat and long from the selected input. This integration streamlines city input "
               "and improves accuracy by using real-time data from Google Maps, ensuring a smooth and efficient user "
               "experience.",
    "category": "Services",
    "version": "16.0.1.0.0",
    'author': 'QWY Software PVT Ltd',
    'company': 'QWY Software PVT Ltd',
    'maintainer': 'QWY Software PVT Ltd',
    "contributor": "QWY Software PVT Ltd",
    "website": "https://qwysoft.com",
    "support": "support@qwysoft.com",
    "depends": ['base', 'base_setup'],
    "data":[
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'qwy_google_geo_locator_widget/static/src/js/qwy_google_geo_locator_widget.js',
            'qwy_google_geo_locator_widget/static/src/xml/qwy_google_geo_locator_widget.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    "installable": True,
    "application": True,
    "auto_install": False,
}