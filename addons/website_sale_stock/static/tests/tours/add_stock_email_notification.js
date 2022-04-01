/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('add_stock_email_notification_product', {
        test: true,
        url: '/shop?search=Macbook%20Pro',
    },
    [
        {
            content: "Open product page",
            trigger: '.oe_product_cart a:contains("Macbook Pro")',
        },
        {
            content: "Click on 'Be notified when back in stock'",
            trigger: '#add_stock_email_notification_product_message',
        },
        {
            content: "Fill email form",
            trigger: 'div[id="add_stock_email_notification_product_form"] input[name="email"]',
            run: 'text test@test.test',
        },
        {
            content: "Click on the button",
            trigger: '#add_stock_email_notification_product_form_button',
        },
        {
            content: "Success Message",
            trigger: '#add_stock_email_notification_product_success_message',
        },
    ],
);

