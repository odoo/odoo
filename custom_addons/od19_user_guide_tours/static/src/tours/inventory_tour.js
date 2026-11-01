import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Inventory Operations Tour
 *
 * Walks the user through:
 *  1. Stock Audit Counting (full audit count sessions)
 *  2. Service Card (preventive maintenance)
 *  3. QC Inspection (incoming / outgoing quality control)
 *  4. Transportation Order (vehicle, route, delivery tracking)
 */
registry.category("web_tour.tours").add("od19_inventory_operations_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's explore <b>Inventory Operations</b>: service cards, QC, and transport."))
        ),

        // --- Service Card ---
        {
            trigger: navSection('Products'),
            content: markup(_t("Open the <b>Products</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Service Cards'),
            content: markup(_t(
                "Open <b>Service Cards</b> to track preventive maintenance for equipment."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new service card."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='service_date'] .o_input",
            content: _t("Set the service date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='service_type'] .o_select_menu_toggler",
            content: _t("Choose the service type (preventive, corrective, etc.)."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the customer."),
            run: "edit Tesla",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Tesla')",
            content: _t("Pick the customer from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: _t("Select the product / equipment being serviced."),
            run: "edit Communication",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Communication')",
            content: _t("Pick the product from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='technician_id'] input",
            content: _t("Assign the responsible technician."),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t("Click <b>Confirm</b> when the service is scheduled.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_done']",
            content: markup(_t(
                "Click <b>Done</b> once the service is completed. " +
                "The <b>Next Service Date</b> is calculated automatically from the service interval."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- QC Inspection ---
        {
            trigger: navSection('Products'),
            content: markup(_t("Open the <b>Products</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('QC Inspections'),
            content: markup(_t(
                "Open <b>QC Inspections</b> for incoming and outgoing quality control."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new QC inspection."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='inspection_type'] .o_select_menu_toggler",
            content: _t("Select inspection type: incoming, outgoing, or in-process."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the supplier or customer."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: _t("Select the product to inspect."),
            run: "edit Communication",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Communication')",
            content: _t("Pick the product from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='qty_tested'] input",
            content: _t("Enter the quantity tested."),
            run: "edit 10",
        },
        {
            trigger: ".o_field_widget[name='qty_accepted'] input",
            content: _t("Enter the quantity accepted."),
            run: "edit 9",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_x2many_list_row_add a",
            content: markup(_t(
                "Add <b>inspection lines</b>: each parameter with expected vs. actual value and pass/fail result."
            )),
            run: "click",
        },
        {
            trigger: ".o_selected_row",
        },
        {
            trigger: ".o_selected_row .o_field_widget[name='parameter'] input",
            content: _t("Enter the inspection parameter name."),
            run: "edit Surface finish",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>Start</b> to begin the inspection.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_pass']",
            content: markup(_t("Click <b>Pass</b> if all criteria are met, or <b>Fail</b> otherwise.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Transportation ---
        {
            trigger: navSection('Products'),
            content: markup(_t("Open the <b>Products</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Transportation')",
            content: markup(_t(
                "Open the <b>Transportation</b> menu to manage delivery vehicles and routes."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Transport Orders'),
            content: markup(_t("Open <b>Transport Orders</b> to track deliveries.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new transport order."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date'] .o_input",
            content: _t("Set the transport date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='vehicle_id'] input",
            content: _t("Select the vehicle."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='vehicle_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the vehicle from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='driver_id'] input",
            content: _t("Select the driver."),
            run: "edit Administrator",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Administrator')",
            content: _t("Pick the driver from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='route_id'] input",
            content: _t("Select the transport route (origin → destination)."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='origin_location'] input",
            content: _t("Enter the origin location."),
            run: "edit Bangkok",
        },
        {
            trigger: ".o_field_widget[name='destination_location'] input",
            content: _t("Enter the destination location."),
            run: "edit Chiang Mai",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t("<b>Confirm</b> the transport order.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_start_transit']",
            content: markup(_t("Click <b>Start Transit</b> when the vehicle departs.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_deliver']",
            content: markup(_t("Click <b>Deliver</b> when the goods arrive at the destination.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Inventory operations complete! You've learned full-audit <b>stock counting</b>, " +
                "<b>service cards</b> for maintenance, <b>QC inspections</b> with pass/fail criteria, " +
                "and <b>transport orders</b> from draft to delivered."
            )),
            run: "click",
        },
    ],
});
