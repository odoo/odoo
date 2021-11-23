{
    'name': 'Calendar - iCal',
    'version': '1.0',
    'summary': 'Enable download of user calendars as iCal.',

    'author': 'MetricWise, Inc.',
    'license': 'LGPL-3',
    'category': 'Tools',

    'depends': [
        'calendar',
        'web',
    ],

    'external_dependencies': {
        'python': [
            'vobject',
        ],
    },

    'assets': {
        'web.assets_backend': [
            'calendar_ical/static/src/js/*.js',
        ],
        'web.assets_qweb': [
            'calendar_ical/static/src/xml/*.xml',
        ],
    },

    'data': [
        'views/res_users_views.xml',
    ],
}
