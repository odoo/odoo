import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('back_in_stock_notification_product', {
        url: '/shop?search=Macbook%20Pro',
    steps: () => [
        {
            content: "Open product page",
            trigger: 'a:contains("Macbook Pro")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Click on 'Be notified when back in stock'",
            trigger: '#product_stock_notification_message',
            run: "click",
        },
        {
            content: "Fill email form",
            trigger: 'div[id="stock_notification_form"] input[name="email"]',
            run: "edit test@test.test",
        },
        {
            content: "Click on the button",
            trigger: '#product_stock_notification_form_submit_button',
            run: "click",
        },
        {
            content: "Success Message",
            trigger: '#stock_notification_success_message',
        },
    ],
});
