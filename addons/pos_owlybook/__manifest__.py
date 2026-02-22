{
    'name': "Owlybook",
    'summary': "Browse and interact with Odoo UI components.",
    'description': "Owlybook allows you to explore and interact with Odoo UI components through multiple stories.",
    'author': "Florent Dardenne & Maximilien La Barre",
    'website': "https://github.com/fdardenne/odoo-storybook",
    'category': 'Productivity/Owlybook',
    'version': '0.1',
    'depends': ['point_of_sale'],
    'data': [
        'views/owlybook_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_owlybook/static/src/js/**/*.scss',
        ],
        'pos_owlybook.assets_owlybook': [
            ('include', 'web.assets_backend'),
            'point_of_sale/static/src/app/utils/use_timed_press.js',
            'point_of_sale/static/src/app/components/centered_icon/centered_icon.js',
            'point_of_sale/static/src/app/components/orderline/orderline.js',
            'point_of_sale/static/src/app/components/orderline/orderline.xml',
            'point_of_sale/static/src/app/components/order_display/order_display.js',
            'point_of_sale/static/src/app/components/order_display/order_display.xml',
            # 'point_of_sale/static/src/app/components/numpad/numpad.js',
            # 'point_of_sale/static/src/app/components/numpad/numpad.xml',
            'pos_owlybook/static/src/js/**/*.js',
            'pos_owlybook/static/src/js/**/*.xml',
            'pos_owlybook/static/src/stories/**/*',
        ],
    },
    'application': True,
    'license': 'LGPL-3',
}
