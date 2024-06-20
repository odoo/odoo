/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@test_sale_product_configurators/js/tour_utils";

registry.category("web_tour.tours").add('event_sale_with_product_configurator_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    run: "click",
}, {
    trigger: '.o_list_button_add',
    extra_trigger: ".o_sale_order",
    run: "click",
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: "edit Tajine Saucisse",
}, {
    isActive: ["auto"],
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    run: "click",
}, {
    trigger: 'a:contains("Add a product")',
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: "edit event (",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Registration Event (TEST variants)")',
    run: "click",
}, {
    trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Memorabilia")) button:has(i.fa-plus)',
    run: "click",
}, {
    trigger: 'button:contains(Confirm)',
    run: "click",
}, {
    trigger: '.o_input_dropdown input',
    extra_trigger: '.o_technical_modal',  // to be in the event wizard
    run: "edit Test",
}, {
    trigger: 'div[name="event_id"] input',
    run: "click",
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    in_modal: false,
    run: "click",
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Kid + meal")',
    in_modal: false,
    run: "click",
}, {
    trigger: '.o_event_sale_js_event_configurator_ok',
    run: "click",
}, {
    trigger: 'a:contains("Add a product")',
    extra_trigger: 'td[name="price_subtotal"]:contains("16.50")',  // wait for the optional product line
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    extra_trigger: '.o_data_row:nth-child(3)',  // wait for the new row to be created
    run: "edit event (",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Registration Event (TEST variants)")',
    run: "click",
}, {
    trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Registration Event (TEST variants)")) label:contains("Adult")',
    run: "click",
}, {
    trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Registration Event (TEST variants)")) .o_sale_product_configurator_qty input',
    run: "edit 5 && click body",
},
    configuratorTourUtils.assertPriceTotal("150.00"),
{
    trigger: 'button:contains(Confirm)',
    run: "click",
}, {
    trigger: '.o_input_dropdown input',
    extra_trigger: '.o_technical_modal',
    run: "edit Test",
}, {
    trigger: 'div[name="event_id"] input',
    run: "click",
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    in_modal: false,
    run: "click",
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Adult")',
    in_modal: false,
    run: "click",
}, {
    trigger: '.o_event_sale_js_event_configurator_ok',
    run: "click",
}, {
    trigger: 'a:contains("Add a product")',
    extra_trigger: 'td[name="price_subtotal"]:contains("150.00")',  // wait for the adult tickets line
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    extra_trigger: '.o_data_row:nth-child(4)',  // wait for the new row to be created
    run: "edit event (",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Registration Event (TEST variants)")',
    run: "click",
}, {
    trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Registration Event (TEST variants)")) label:contains("VIP")',
    run: "click",
},
    configuratorTourUtils.assertPriceTotal(60.00),
{
    trigger: 'button:contains(Confirm)',
    run: "click",
}, {
    trigger: '.o_input_dropdown input',
    extra_trigger: '.o_technical_modal',
    run: "edit Test",
}, {
    trigger: 'div[name="event_id"] input',
    run: "click",
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    in_modal: false,
    run: "click",
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("VIP")',
    in_modal: false,
    run: "click",
}, {
    trigger: '.o_event_sale_js_event_configurator_ok',
    run: "click",
}, ...stepUtils.saveForm({ extra_trigger: '.o_field_cell.o_data_cell.o_list_number:contains("60.00")' }),
]});
