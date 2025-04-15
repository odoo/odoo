/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('event_configurator_tour', {
    url: "/web",
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'enterprise'
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order"
}, {
    trigger: "a:contains('Add a product')"
}, {
    trigger: 'div[name="product_id"] input, div[name="product_template_id"] input',
    run: function (actions) {
        actions.text('Event Registration');
    }
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
    trigger: '.o_event_sale_js_event_configurator_ok'
}, {
    trigger: "td[name='name'][data-tooltip*='VIP']",
    run: function () {} // check
}, {
    trigger: 'ul.nav a:contains("Order Lines")',
    run: 'click'
}, {
    content: "search the partner",
    trigger: 'div[name="partner_id"] input',
    run: 'text Azure'
}, {
    content: "select the partner",
    trigger: 'ul.ui-autocomplete > li > a:contains(Azure)',
}, {
    trigger: 'td:contains("Event")',
    run: 'click'
}, {
    trigger: 'button.fa-pencil'
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click'
}, {
    trigger: 'ul.ui-autocomplete a:contains("Standard")',
    run: 'click',
    in_modal: false
}, {
    trigger: '.o_event_sale_js_event_configurator_ok'
}, {
    trigger: "td[name='name'][data-tooltip*='Standard']",
    run: function () {} // check
}, ...stepUtils.saveForm()
]});
