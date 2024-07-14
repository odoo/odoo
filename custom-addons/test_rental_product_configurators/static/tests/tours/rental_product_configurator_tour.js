/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@test_sale_product_configurators/js/tour_utils";

registry.category("web_tour.tours").add('rental_product_configurator_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale_renting.rental_menu_root"]',
    edition: 'enterprise'
}, {
    trigger: '.o-kanban-button-new',
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")'
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custom',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
},
// Product Configurator Wizard
    configuratorTourUtils.selectAttribute("Customizable Desk", "Legs", "Aluminium"),
    // Check on the style to ensure that the color is the one set in backend.
    configuratorTourUtils.selectAttribute("Customizable Desk", "Color", "Black", "color"),
{
    trigger: '.btn-primary:disabled:contains("Confirm")',
    isCheck: true, // check confirm button is disabled
},
    // Check on the style to ensure that the color is the one set in backend.
    configuratorTourUtils.selectAttribute("Customizable Desk", "Color", "White", "color"),
{
    trigger: '.btn-primary:not(:disabled):contains("Confirm")',
    isCheck: true, // check confirm is available
},
    configuratorTourUtils.addOptionalProduct("Conference Chair"),
    configuratorTourUtils.addOptionalProduct("Chair floor protection"),
{
    trigger: 'button:contains(Confirm)',
    id: 'quotation_product_selected',
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST)")',
    run: "click",
}, {
    trigger: ".o_data_row:eq(0) .o_data_cell[name='product_uom_qty'] input",
    run: "text 2.0",
}, {
    trigger: ".o_data_row:eq(0) .o_data_cell[name='price_unit'] input",
    run: "text 42.0",
}, {
    content: 'Wait for the unit price to be rerendered.',
    trigger: '.o_selected_row [name=price_unit] input:propValue(42.00)',
    run() {},
},

// Adding a line with a more expensive custom desk
{
    trigger: 'a:contains("Add a product")',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custom',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
},
// Product Configurator Wizard
    configuratorTourUtils.selectAttribute("Customizable Desk", "Legs", "Steel"),
    // Check on the style to ensure that the color is the one set in backend.
    configuratorTourUtils.selectAttribute("Customizable Desk", "Color", "Black", "color"),
{
    trigger: '.btn-primary:not(:disabled):contains("Confirm")',
    isCheck: true, // check confirm is available
}, {
    trigger: 'button:contains(Confirm)',
    id: 'quotation_product_selected',
}, {
    trigger: ".o_data_row:eq(3) .o_data_cell[name='product_uom_qty']",
    run: "click",
}, {
    trigger: ".o_data_row:eq(3) .o_data_cell[name='product_uom_qty'] input",
    run: "text 5.0",
}, {
    trigger: 'button[name=action_confirm]',
    position: 'bottom',
}, {
    content: "verify that the rental has been confirmed",
    trigger: '.o_statusbar_status button.o_arrow_button_current:contains("Sales Order")',
    isCheck: true,
}, ...stepUtils.discardForm(),
]});
