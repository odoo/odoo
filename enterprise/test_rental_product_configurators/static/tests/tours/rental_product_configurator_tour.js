/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('rental_product_configurator_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale_renting.rental_menu_root", "Open the rental app"),
        {
            trigger: '.o-kanban-button-new',
            run: "click",
        },
        ...tourUtils.selectCustomer("Tajine Saucisse"),
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        // Product Configurator Wizard
        configuratorTourUtils.selectAttribute("Customizable Desk", "Legs", "Aluminium"),
        // Check on the style to ensure that the color is the one set in backend.
        configuratorTourUtils.selectAttribute("Customizable Desk", "Color", "Black", "color"),
        {
            trigger: '.btn-primary:disabled:contains("Confirm")',
        },
        // Check on the style to ensure that the color is the one set in backend.
        configuratorTourUtils.selectAttribute("Customizable Desk", "Color", "White", "color"),
        {
            trigger: '.btn-primary:not(:disabled):contains("Confirm")',
        },
        configuratorTourUtils.addOptionalProduct("Conference Chair"),
        configuratorTourUtils.addOptionalProduct("Chair floor protection"),
        {
            trigger: ".modal:not(.o_inactive_modal) button:contains(Confirm)",
            id: 'quotation_product_selected',
            run: "click",
        },
        {
            trigger: 'td.o_data_cell:contains("Customizable Desk (TEST)")',
            run: "click",
        },
        {
            trigger: ".o_data_row:eq(0) .o_data_cell[name='product_uom_qty'] input",
            run: "edit 2.0 && click .o_selected_row",
        },
        {
            trigger: ".o_data_row:eq(0) .o_data_cell[name='price_unit'] input",
            run: "edit 42.0 && click .o_selected_row",
        },
        {
            content: 'Wait for the unit price to be rerendered.',
            trigger: '.o_selected_row [name=price_unit] input:value(42.00)',
        },
        // Adding a line with a more expensive custom desk
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        // Product Configurator Wizard
        configuratorTourUtils.selectAttribute("Customizable Desk", "Legs", "Steel"),
        // Check on the style to ensure that the color is the one set in backend.
        configuratorTourUtils.selectAttribute("Customizable Desk", "Color", "Black", "color"),
        {
            trigger: '.btn-primary:not(:disabled):contains("Confirm")',
        },
        {
            trigger: ".modal:not(.o_inactive_modal) button:contains(Confirm)",
            id: 'quotation_product_selected',
            run: "click",
        },
        {
            trigger: ".o_data_row:eq(3) .o_data_cell[name='product_uom_qty']",
            run: "click",
        },
        {
            trigger: ".o_data_row:eq(3) .o_data_cell[name='product_uom_qty'] input",
            run: "edit 5.0",
        },
        {
            trigger: 'button[name=action_confirm]',
            run: "click",
        },
        {
            content: "verify that the rental has been confirmed",
            trigger: '.o_statusbar_status button.o_arrow_button_current:contains("Sales Order")',
        },
        {
            //Nothing to discard (button is not visible)
            content: "check the form is saved",
            trigger: ".o_form_view > div > div > .o_form_saved",
        },
    ],
});
