/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('add_stock_email_notification_wishlist', {
        test: true,
        url: '/shop/wishlist',
    },
    [
        {
            content: "Click on 'Be notified when back in stock'",
            trigger: '#add_stock_email_notification_wishlist_button',
        },
        {
            content: "Fill email form",
            trigger: 'div[id="add_stock_email_notification_wishlist_form"] input[name="email"]',
            run: 'text test@test.test',
        },
        {
            content: "Click on the button",
            trigger: '#add_stock_email_notification_wishlist_form_button',
        },
        {
            content: "Success Message",
            trigger: '#add_stock_email_notification_wishlist_success_message',
        },

    ],
);

