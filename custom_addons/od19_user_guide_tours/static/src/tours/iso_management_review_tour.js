import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Management Review Tour
 *
 * Walks the user through the management review lifecycle:
 *  Draft → Planned → In Progress → Reviewed → Closed
 */
registry.category("web_tour.tours").add("od19_iso_management_review_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's conduct a <b>Management Review</b> of the management system."))
        ),

        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('การทบทวนระบบจัดการ')",
            content: markup(_t("Open the <b>การทบทวนระบบจัดการ (Management Review)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('รายการการทบทวน'),
            content: markup(_t("Open the <b>รายการการทบทวน</b> list.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // Switching action is asynchronous: the previous list stays mounted for
        // a few frames, so `.o_list_button_add` would click the *previous*
        // list's "New" button. Wait for the target action to be on screen.
        waitForAction('การทบทวนระบบจัดการ'),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new management review meeting."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='title'] input",
            content: _t("Enter the review name."),
            run: "edit Management Review Meeting Q4 2026",
        },
        {
            trigger: ".o_field_widget[name='date'] .o_input",
            content: _t("Set the review meeting date."),
            run: "edit 2026-04-01",
        },
        {
            trigger: ".o_field_widget[name='chairman_id'] input",
            content: _t("Set the lead reviewer (top management)."),
            run: "click",
        },
        {
            // Scope the selector to the `chairman_id` field itself.
            // `:not(.o_loading)` on the dropdown menu is NOT reliable: Odoo
            // marks the *inline* loading entry (`a.o_loading.dropdown-item`),
            // not the `<ul>`, so the menu keeps that class off while another
            // field's stale/hidden dropdown may still be mounted. Targeting
            // `[name='chairman_id'] .o-autocomplete--dropdown-menu
            // a.dropdown-item:not(.o_loading)` guarantees we click the freshly
            // loaded suggestion of *this* field.
            trigger: ".o_field_widget[name='chairman_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Management Review Workflow ---
        {
            trigger: "button[name='action_plan']",
            content: markup(_t("Click <b>วางแปรยัง</b> (Plan) to schedule the review.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>เริ่มประชุม</b> (Start) when the meeting begins.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_reviewed']",
            content: markup(_t(
                "Click <b>ทบทวนแล้ว</b> (Reviewed) when all inputs have been discussed " +
                "(audit results, customer feedback, process performance, etc.)."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_close']",
            content: markup(_t(
                "Click <b>ปิด</b> (Close) to finalize the review. " +
                "Decisions and actions should be recorded before closing."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Management Review complete! Workflow: " +
                "<b>Draft → Planned → In Progress → Reviewed → Closed</b>. " +
                "Management review ensures the QMS remains suitable, adequate, and effective."
            )),
            run: "click",
        },
    ],
});
