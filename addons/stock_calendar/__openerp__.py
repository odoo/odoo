# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendars on Orderpoints',
    'version': '1.0',
    'summary': 'Calendars ',
    'description': """
        The stock_calendar module handles minimum stock rules (=orderpoints / reordering rules) differently by
        the possibility to take into account the purchase and delivery calendars.

        Normally, the scheduler will go through all orderpoints and will create a procurement with a quantity taking
        into account the current stock and all future stock moves.  For companies working with fresh products, this is
        a problem, because if you order the products needed over 2 weeks now and they arrive tomorrow, then
        these products won't be fresh anymore in two weeks.

        To solve this, we added a delivery calendar to the orderpoint.  The future stock moves (they represent the needs)
        taken into account will be limited to those until the second delivery according to the calendar.
        So if I am delivered every week on Tuesday and on Friday, when I order on Monday, I will be delivered on Tuesday
        with all what is needed until Friday.

        This however is not good enough as you want to create a purchase order only before the date of the delivery as the
        future needs might change.  (otherwise you could have ordered too much already)  For this, we added a
        purchase calendar and the orderpoint will only be triggered when the scheduler is run within the time specified
        by the purchase calendar.  (a last execution date will also check if it has not already been triggered within this time)

        However, sometimes we have double orders: suppose we need to order twice on Friday: a purchase order for Monday
        and a purchase order for Tuesday.  Then we need to have two orders at the same time.
        To handle this, we put a procurement group on the calendar line and for the purchase calendar line we need to do,
        we will check the corresponding delivery line.  On the procurement group, we can tell to propagate itself to the purchase
        and this way it is possible to have an order for Monday and one for Tuesday.

        With normal orderpoints, the dates put on the purchase order are based on the delays in the system for the product/company.
        This does not correspond to what is done with the calendars, so the purchase/delivery dates will be set according to the calendars also.

        The calendars we use are on weekly basis.  It is possible however to have a start date and end date for e.g. the Tuesday delivery.
        It is also possible to put exceptions for days when there is none.
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'images': [],
    'depends': ['purchase', 'resource'],
    'category': 'Warehouse',
    'sequence': 16,
    'demo': [

    ],
    'data': [
        'stock_calendar_view.xml'
    ],
    'test': [
        'test/orderpoint_calendar.yml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'qweb': [],
}
