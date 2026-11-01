import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Misc Features Tour
 *
 * Walks the user through:
 *  1. Runtime Guard - environment / version health check
 *  2. Repeat Customer Enhanced - repeat-business analysis report
 */
registry.category("web_tour.tours").add("od19_misc_features_tour", {
    url: "/odoo",
    steps: () => [
        // The "Misc Features" toolbox is nested inside the standard Settings app
        // (it is a technical module, not a standalone app).
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("Let's explore the <b>Misc Features</b>: Runtime Guard and Repeat Customer analysis."))
        ),

        // --- Runtime Guard (Settings > Misc Features > Runtime Guard) ---
        {
            trigger: navSection("Misc Features"),
            content: markup(_t("Open the <b>Misc Features</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Run Runtime Check"),
            content: markup(_t(
                "Open <b>Run Runtime Check</b> to capture the current Odoo version, Python version, " +
                "installed-module count and database size."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "footer button[name='action_run_check']",
            content: markup(_t(
                "Click <b>Run Check</b> to execute the guard. The result is stored as a history record " +
                "for later comparison."
            )),
            tooltipPosition: "top",
            run: "click",
        },
        {
            // "Run Check" persists the snapshot and re-opens it with
            // `target: "current"`, so the wizard dialog closes and the snapshot
            // form replaces the main action.
            //
            // The server-side check runs `SELECT pg_database_size(...)`, which
            // can take tens of seconds on a large database, so this step needs a
            // far longer timeout than the 10 s default. Waiting directly for the
            // snapshot form avoids acting on the dialog/backdrop while the
            // dialog is still tearing down (which aborts with "not allowed to do
            // action on an element that's below a modal").
            trigger: ".o_form_view .o_field_widget[name='odoo_version']",
            content: markup(_t(
                "Each check is logged with the date, versions and metrics, so you can track " +
                "environment drift over time."
            )),
            timeout: 90000,
            run: "click",
        },

        // --- Repeat Customer Enhanced (Settings > Misc Features) ---
        {
            trigger: navSection("Misc Features"),
            content: markup(_t("Re-open the <b>Misc Features</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Repeat Customer Enhanced"),
            content: markup(_t(
                "Open <b>Repeat Customer Enhanced</b> to analyse repeat business."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Confirmed sale orders are grouped by the <b>actual partner</b> (shipping partner " +
                "if set, otherwise the customer), showing <b>last order date</b>, <b>order count</b> " +
                "and <b>total amount</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Use this report to identify your most loyal contractors and project owners, " +
                "and to spot repeat-business opportunities."
            )),
            run: "click",
        },
    ],
});
