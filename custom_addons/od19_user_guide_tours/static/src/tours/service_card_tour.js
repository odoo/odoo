import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Service Card Tour
 *
 * Walks the user through the service cards (บัตรบริการ) of od19_service_card:
 *  1. Inventory > Products > Service Cards
 *  2. Review the list: SLA flags and the next service date
 *  3. Open a card, review the SLA & time tracking, run Confirm -> Done
 */
registry.category("web_tour.tours").add("od19_service_card_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's follow the <b>Service Cards</b> of the after-sales activity."))
        ),
        {
            trigger: navSection('Products'),
            content: markup(_t("Open the <b>Products</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Service Cards'),
            content: markup(_t("Open <b>Service Cards</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Service Cards"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line is one service intervention: the <b>customer</b>, the <b>product</b>, " +
                "the <b>service type</b> and the <b>next service date</b> used to schedule the " +
                "next visit."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            content: markup(_t(
                "Use the filters and <b>Group By</b> to isolate <b>SLA Breached</b> cards, or to " +
                "group them by Customer, Product or Type."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to record a service card.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Fill in the <b>service date</b>, the <b>type</b> and the <b>interval</b>, then " +
                "the customer, product, lot and technician. The <b>next service date</b> is " +
                "computed automatically."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='sla_hours']",
            content: markup(_t(
                "In <b>SLA &amp; Time Tracking</b> set the contracted <b>SLA hours</b>; the " +
                "deadline, the breach flag and the duration are then tracked for you."
            )),
            run: "click",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Workflow: <b>Confirm</b> → <b>Done</b>. Use <b>Reset to Draft</b> to reopen a " +
                "cancelled card and <b>Cancel</b> to abort it."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Service Card tour complete! Keep the SLA under control and schedule the next " +
                "service on time."
            )),
            run: "click",
        },
    ],
});
