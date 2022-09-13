/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('event_sale_with_product_configurator_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    trigger: '.o_list_button_add',
    extra_trigger: ".o_sale_order",
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: "a:contains('Add a product')",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text event (',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Registration Event (TEST variants)")',
}, {
    trigger: '.js_product:has(strong:contains(Memorabilia)) .js_add',
    extra_trigger: '.oe_advanced_configurator_modal',
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',  // to confirm the first wizard
}, {
    trigger: '.o_input_dropdown input',
    extra_trigger: '.o_technical_modal',  // to be in the event wizard
}, {
    trigger: 'div[name="event_id"] input',
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    in_modal: false,
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Kid + meal")',
    in_modal: false,
}, {
    trigger: '.o_event_sale_js_event_configurator_ok'
}, {
    trigger: 'a:contains("Add a product")',
    extra_trigger: '.o_monetary_cell span:contains("16.50")',  // wait for the optional product line
}, {
    trigger: 'div[name="product_template_id"] input',
    extra_trigger: '.o_field_many2one[name="product_template_id"] .o_dropdown_button',
    run: 'text event (',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Registration Event (TEST variants)")',
}, {
    trigger: '.radio_input_value span:contains(Adult)',
}, {
    trigger: '.js_quantity',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'text 5',
}, {
    trigger: '.js_price_total span:contains("150.00")',  // to be sure the correct variant is set
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
}, {
    trigger: '.o_input_dropdown input',
    extra_trigger: '.o_technical_modal',
}, {
    trigger: 'div[name="event_id"] input',
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    in_modal: false,
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Adult")',
    in_modal: false,
}, {
    trigger: '.o_event_sale_js_event_configurator_ok'
}, {
    trigger: 'a:contains("Add a product")',
    extra_trigger: '.o_monetary_cell span:contains("150.00")',  // wait for the adult tickets line
}, {
    trigger: 'div[name="product_template_id"] input',
    extra_trigger: '.o_field_many2one[name="product_template_id"] .o_dropdown_button',
    run: 'text event (',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Registration Event (TEST variants)")',
}, {
    trigger: '.radio_input_value span:contains(VIP)',
}, {
    trigger: '.js_price_total span:contains("60.00")',  // to be sure the correct variant is set
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
}, {
    trigger: '.o_input_dropdown input',
    extra_trigger: '.o_technical_modal',
}, {
    trigger: 'div[name="event_id"] input',
}, {
    trigger: 'ul.ui-autocomplete a:contains("TestEvent")',
    in_modal: false,
}, {
    trigger: 'div[name="event_ticket_id"] input',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete a:contains("VIP")',
    in_modal: false,
}, {
    trigger: '.o_event_sale_js_event_configurator_ok',
}, ...tour.stepUtils.saveForm({ extra_trigger: '.o_field_cell.o_data_cell.o_list_number:contains("60.00")' }),
]);
