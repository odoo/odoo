import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Apps Filter Tour
 *
 * Shows the custom "OD19 Modules" Apps entry added by od19_apps_filter:
 *  1. Open Settings > OD19 Modules (a pre-filtered Apps view)
 *  2. Read the module cards
 *  3. Discover the three saved filters (OD19 Modules / New Apps / New OD19 Apps)
 */
registry.category("web_tour.tours").add("od19_apps_filter_tour", {
    url: "/odoo",
    steps: () => [
        // The entry is nested inside the standard Settings app.
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("Let's open the pre-filtered <b>OD19 Modules</b> Apps view."))
        ),
        {
            trigger: navSection("OD19 Modules"),
            content: markup(_t("Open <b>OD19 Modules</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("OD19 Modules"),
        {
            trigger: ".o_kanban_view, .o_list_view",
            content: markup(_t(
                "This Apps view lists only the custom modules whose technical name starts " +
                "with <b>od19_</b>, so the ~1,200 standard modules stay out of the way."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            content: markup(_t("Open the <b>search</b> panel to reach the saved filters.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_filter_menu .o_menu_item:text('OD19 Modules')",
            content: markup(_t(
                "Three shortcuts are available: <b>OD19 Modules</b> (all custom modules), " +
                "<b>New Apps</b> (not yet installed) and <b>New OD19 Apps</b> (custom modules " +
                "still to install)."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            content: markup(_t("Close the search panel to return to the list.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_kanban_view, .o_list_view",
            content: markup(_t(
                "OD19 Modules tour complete! Activate or upgrade any custom module directly " +
                "from this filtered view."
            )),
            run: "click",
        },
    ],
});
