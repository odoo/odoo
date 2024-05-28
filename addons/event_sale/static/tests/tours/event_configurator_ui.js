/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('event_configurator_tour', {
    url: "/web",
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'community',
    run: "click",
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'enterprise',
    run: "click",
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order",
    run: "click",
}, {
    trigger: "a:contains('Add a product')",
    run: "click",
}, {
    trigger: 'div[name="product_id"] input, div[name="product_template_id"] input',
    run: "edit Event Registration",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Event Registration")',
    run: 'click'
}, {
    trigger: 'div[name="event_id"] input',
    run: 'click'
}, {
    trigger: 'ul.ui-autocomplete a:contains("Design")',
    run: 'click',
    in_modal: false
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click'
}, {
    trigger: 'ul.ui-autocomplete a:contains("VIP")',
    run: 'click',
    in_modal: false
}, {
    trigger: '.o_event_sale_js_event_configurator_ok',
    run: "click",
}, {
    trigger: 'label:contains("Untaxed Amount")',
    run: "click",
    // click somewhere else to exit cell focus
}, {
    trigger: "td[name='name'] span:contains('VIP')",
    run: () => {}, // check
}, {
    trigger: 'ul.nav a:contains("Order Lines")',
    run: 'click'
}, {
    content: "search the partner",
    trigger: 'div[name="partner_id"] input',
    run: "edit Azure",
}, {
    content: "select the partner",
    trigger: 'ul.ui-autocomplete > li > a:contains(Azure)',
    run: "click",
}, {
    trigger: 'td:contains("Event")',
    run: 'click'
}, {
    trigger: 'button.fa-pencil',
    run: "click",
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click'
}, {
    trigger: 'ul.ui-autocomplete a:contains("Standard")',
    run: 'click',
    in_modal: false
}, {
    trigger: '.o_event_sale_js_event_configurator_ok',
    run: "click",
}, {
    trigger: 'label:contains("Untaxed Amount")',
    run: "click",
    // click somewhere else to exit cell focus
}, {
    trigger: "td[name='name'] span:contains('Standard')",
    run: () => {}, // check
}, ...stepUtils.saveForm()
]});
