import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Nonconformity / CAPA Tour
 *
 * Walks the user through the NC/CAPA lifecycle:
 *  Draft → Open → Analysis → Action → Verification → Closed
 */
registry.category("web_tour.tours").add("od19_iso_nonconformity_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's manage <b>Nonconformity / CAPA</b> from detection to closure."))
        ),

        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('ไม่สอดคล้อง / CAPA')",
            content: markup(_t("Open the <b>ไม่สอดคล้อง / CAPA</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('รายการไม่สอดคล้อง'),
            content: markup(_t("Open <b>รายการไม่สอดคล้อง (Nonconformities)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // Switching action is asynchronous: the previous list stays mounted for
        // a few frames, so `.o_list_button_add` would click the *previous*
        // list's "New" button (creating a document-control record instead).
        // Wait for the target action to be on screen first.
        waitForAction('ไม่สอดคล้อง / CAPA'),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new nonconformity record."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='title'] input",
            content: _t("Enter the nonconformity title."),
            run: "edit Defective parts found in incoming inspection",
        },
        {
            trigger: ".o_field_widget[name='severity'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>severity</b> (Minor, Major, Critical).")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='source'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>source</b> of the nonconformity (audit, customer complaint, etc.).")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='category'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>category</b> of the nonconformity (quality, environment, safety, etc.).")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='department_id'] input",
            content: _t("Set the responsible department."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='responsible_id'] input",
            content: _t("Set the responsible person."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='due_date'] .o_input",
            content: _t("Set the due date for corrective action."),
            run: "edit 2026-11-30",
        },
        {
            trigger: "a.nav-link:contains('รายละเอียด')",
            content: markup(_t("Open the <b>รายละเอียด (Details)</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='description'] textarea",
            content: _t("Describe the nonconformity in detail."),
            run: "edit 5 units of Part X failed dimensional inspection",
        },
        {
            trigger: ".o_field_widget[name='immediate_action'] textarea",
            content: markup(_t("Describe the <b>immediate (containment) action</b>.")),
            run: "edit Quarantined all affected parts",
        },
        ...stepUtils.saveForm(),

        // --- NC/CAPA Workflow ---
        {
            trigger: "button[name='action_open']",
            content: markup(_t("Click <b>เปิด</b> (Open) to confirm the nonconformity.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('วิเคราะห์สาเหตุ')",
            content: markup(_t("Open the <b>วิเคราะห์สาเหตุ (Root Cause Analysis)</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='root_cause_method'] .o_select_menu_toggler",
            content: markup(_t("Select the <b>root cause method</b> (5 Whys, Fishbone, etc.).")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='root_cause'] textarea",
            content: _t("Describe the identified root cause."),
            run: "edit Tooling wear caused dimensional drift",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_analysis']",
            content: markup(_t("Click <b>วิเคราะห์สาเหตุ</b> (Analysis) to move to the action phase.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('การดำเนินการ')",
            content: markup(_t("Open the <b>การดำเนินการ (Actions)</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='corrective_action'] textarea",
            content: markup(_t("Describe the <b>corrective action</b> (CAPA).")),
            run: "edit Replace worn tooling and implement weekly inspection",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_action']",
            content: markup(_t("Click <b>ดำเนินการ</b> (Action) to move to verification.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('ตรวจสอบและปิด')",
            content: markup(_t("Open the <b>ตรวจสอบและปิด (Verification &amp; Closure)</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='verification_result'] textarea",
            content: markup(_t("Record the <b>verification result</b>.")),
            run: "edit Verification passed - no recurrence in last 3 batches",
        },
        {
            trigger: ".o_field_widget[name='verification_date'] .o_input",
            content: markup(_t("Set the <b>verification date</b> — it is required before the CAPA can be closed.")),
            run: "edit 2026-12-15",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_verification']",
            content: markup(_t("Click <b>ตรวจสอบผล</b> (Verification).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_close']",
            content: markup(_t("Click <b>ปิด</b> (Close) to close the CAPA.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Nonconformity / CAPA complete! Workflow: " +
                "<b>Draft → Open → Analysis → Action → Verification → Closed</b>. " +
                "Always document root cause and corrective actions for audit traceability."
            )),
            run: "click",
        },
    ],
});
