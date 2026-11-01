import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Customer Satisfaction Tour
 *
 * Walks the user through:
 *  1. Creating a customer satisfaction survey
 *  2. Survey workflow: Draft → Sent → Completed → Closed
 *  3. Periodic reporting
 */
registry.category("web_tour.tours").add("od19_iso_customer_satisfaction_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's measure <b>Customer Satisfaction</b> with surveys and reports."))
        ),

        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('ความพึงพอใจลูกค้า')",
            content: markup(_t("Open the <b>ความพึงพอใจลูกค้า (Customer Satisfaction)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('แบบสอบถามความพึงพอใจ'),
            content: markup(_t("Open <b>แบบสอบถามความพึงพอใจ (Surveys)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // The action switch is asynchronous; wait for the target list before
        // clicking "New" so the record lands in the right model.
        waitForAction('ความพึงพอใจลูกค้า'),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new customer satisfaction survey."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: markup(_t(
                "Select the <b>customer</b>. The survey number and the survey " +
                "date (today) are set automatically when the record is saved."
            )),
            run: "edit The Auto-Info",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('The Auto-Info')",
            run: "click",
        },
        ...stepUtils.saveForm(),

        // --- Survey Workflow ---
        {
            trigger: "button[name='action_sent']",
            content: markup(_t("Click <b>ส่งแบบสอบถาม</b> (Sent) when the survey is sent to the customer.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_complete']",
            content: markup(_t("Click <b>ตอบกลับแล้ว</b> (Completed) when the customer responds.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_close']",
            content: markup(_t("Click <b>ปิด</b> (Close) to close the survey.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Periodic Report ---
        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('ความพึงพอใจลูกค้า')",
            content: markup(_t("Open the <b>ความพึงพอใจลูกค้า (Customer Satisfaction)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('รายงานรายงวด'),
            content: markup(_t(
                "Open <b>รายงานรายงวด (Periodic Reports)</b> to aggregate satisfaction scores " +
                "and analyze trends over time."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction('รายงานความพึงพอใจรายงวด'),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Customer Satisfaction complete! Survey workflow: " +
                "<b>Draft → Sent → Completed → Closed</b>. " +
                "Use periodic reports to track satisfaction trends and identify improvement areas."
            )),
            run: "click",
        },
    ],
});
