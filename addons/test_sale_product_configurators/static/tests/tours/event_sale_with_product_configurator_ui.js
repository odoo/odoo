/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";

registry.category("web_tour.tours").add('event_sale_with_product_configurator_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    run: "click",
}, 
{
    trigger: ".o_sale_order",
},
{
    trigger: '.o_list_button_add',
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
}, 
{
    trigger: ".modal .o_input_dropdown input",
    run: "edit Test",
}, {
    trigger: '.modal div[name="event_id"] input',
    run: "click",
}, {
    trigger: "ul.ui-autocomplete a:contains(TestEvent)",
    run: "click",
}, {
    trigger: '.modal div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: "ul.ui-autocomplete a:contains(Kid + meal)",
    run: "click",
}, {
    trigger: ".modal .o_event_sale_js_event_configurator_ok",
    run: "click",
}, 
{
    trigger: 'td[name="price_subtotal"]:contains("16.50")', // wait for the optional product line
},
{
    trigger: 'a:contains("Add a product")',
    run: "click",
}, 
{
    trigger: ".o_data_row:nth-child(3)", // wait for the new row to be created
},
{
    trigger: 'div[name="product_template_id"] input',
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
}, 
{
    trigger: ".modal .o_input_dropdown input",
    run: "edit Test",
}, {
    trigger: '.modal div[name="event_id"] input',
    run: "click",
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    run: "click",
}, {
    trigger: '.modal div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Adult")',
    run: "click",
}, {
    trigger: ".modal .o_event_sale_js_event_configurator_ok",
    run: "click",
}, 
{
    trigger: 'td[name="price_subtotal"]:contains("150.00")', // wait for the adult tickets line
},
{
    trigger: 'a:contains("Add a product")',
    run: "click",
}, 
{
    trigger: ".o_data_row:nth-child(4)", // wait for the new row to be created
},
{
    trigger: 'div[name="product_template_id"] input',
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
}, 
{
    trigger: ".modal .o_input_dropdown input",
    run: "edit Test",
}, {
    trigger: 'div[name="event_id"] input',
    run: "click",
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    run: "click",
}, {
    trigger: '.modal div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("VIP")',
    run: "click",
}, {
    trigger: ".modal .o_event_sale_js_event_configurator_ok",
    run: "click",
},
{
    trigger: '.o_field_cell.o_data_cell.o_list_number:contains("60.00")',
},
...stepUtils.saveForm(),
]});
