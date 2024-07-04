/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("product_attribute_multi_type", {
    url: "/web",
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(),
    {
        content: "navigate to the sale app",
        trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
        run: "click",
    }, 
    {
        trigger: ".o_sale_order",
    },
    {
        content: "create a new order",
        trigger: '.o_list_button_add',
        run: "click",
    }, {
        content: "search the partner",
        trigger: 'div[name="partner_id"] input',
        run: "edit Azure",
    }, {
        content: "select the partner",
        trigger: 'ul.ui-autocomplete > li > a:contains(Azure)',
        run: "click",
    }, {
        content: "Add a product",
        trigger: "a:contains('Add a product')",
        run: "click",
    }, {
        trigger: 'div[name="product_template_id"] input',
        run: 'edit Big Burger'
    }, {
        content: "Choose item",
        trigger: '.ui-menu-item-wrapper:contains("Big Burger")',
        run: "click",
    }, {
        content: "Select the attribute value",
        trigger: 'main.modal-body input[type="checkbox"]',
        run: "click",
    }, {
        content: "Click on Confirm",
        trigger: ".modal button:contains(Confirm)",
        in_modal: false,
        run: "click",
    }, ...stepUtils.saveForm()
]});
