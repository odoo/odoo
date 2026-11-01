import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Transportation Tour
 *
 * Walks the user through a transport order:
 *  1. Open Transport Orders from the Inventory app
 *  2. Create an order (vehicle, driver, route)
 *  3. Follow the draft → confirmed → in transit → delivered workflow
 */
registry.category("web_tour.tours").add("od19_transportation_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's plan a <b>transport order</b> from the Inventory app."))
        ),
        {
            trigger: navSection("Products"),
            content: markup(_t("Open the <b>Products</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Transport Orders"),
            content: markup(_t(
                "Open <b>Transport Orders</b> (Products ▸ Transportation ▸ Transport Orders)."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Transport Orders"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line is a transport order with its <b>vehicle</b>, <b>driver</b>, " +
                "<b>route</b> and <b>status</b>."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to plan a transport.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='vehicle_id'] input",
            content: markup(_t("Select the <b>vehicle</b> that will carry out the transport.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='driver_id'] input",
            content: markup(_t("Select the <b>driver</b>.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='route_id'] input",
            content: markup(_t(
                "Pick a reusable <b>route</b> (origin → destination), or fill the two " +
                "locations manually below."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='distance_km'] input",
            content: markup(_t(
                "Enter the <b>distance</b>; the <b>transport cost</b> and currency are stored " +
                "right beside it."
            )),
            run: "edit 25",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Advance the order with the header buttons: <b>Confirm</b> → " +
                "<b>Start Transit</b> → <b>Deliver</b>. The <b>Transfers</b> tab links the " +
                "stock pickings carried by this trip."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Transportation tour complete! Maintain the reusable itineraries under " +
                "<b>Transport Routes</b>."
            )),
            run: "click",
        },
    ],
});
