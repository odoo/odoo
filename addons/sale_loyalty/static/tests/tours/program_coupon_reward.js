import { delay } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import tourUtils from '@sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('program_coupon_reward_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps('sale.sale_menu_root', "Open the sales app"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Test Partner"),
        ...tourUtils.addProduct("Product A"),
        // need to delay for onchange to finish first
        {
            content: "Apply For Coupon",
            trigger: "div[name='so_button_below_order_lines'] > button:nth-child(1)",
            async run(helpers) {
                await delay(50);
                await helpers.click();
            },
        },
        {
            content: "Enter Coupon",
            trigger: "div[name='coupon_code'] input",
            run: "edit test_10dis"
        },
        {
            content: "Apply Coupon Code",
            trigger: "button[name='action_apply']",
            run: "click"
        },
        {
            content: "Close Reward Dialog Box",
            trigger: "header.modal-header button.btn-close",
            run: "click"
        },
        {
            content: "Apply For Coupon Again",
            trigger: "div[name='so_button_below_order_lines'] > button:nth-child(1)",
            run: "click"
        },
        {
            content: "Enter Same Coupon Code",
            trigger: "div[name='coupon_code'] input",
            run: "edit test_10dis"
        },
        {
            content: "Apply",
            trigger: "button[name='action_apply']",
            run: "click"
        },
        {
            content: "Choose Reward",
            trigger: "input[name='radio_field_1']",
            run: "check"
        },
        {
            content: "Apply Reward",
            trigger: "button[name='action_apply']",
            run: "click"
        },
    ]
});
