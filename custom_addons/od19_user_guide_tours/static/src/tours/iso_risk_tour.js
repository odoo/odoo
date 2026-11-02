import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Risk & Opportunity Tour
 *
 * Walks the user through the risk management lifecycle:
 *  Draft → Identified → Analyzed → Evaluated → Treated → Monitored → Closed
 */
registry.category("web_tour.tours").add("od19_iso_risk_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's manage <b>Risks &amp; Opportunities</b> from identification to closure."))
        ),

        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('ความเสี่ยงและโอกาส')",
            content: markup(_t("Open the <b>ความเสี่ยงและโอกาส (Risk &amp; Opportunity)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('รายการความเสี่ยง/โอกาส'),
            content: markup(_t("Open the <b>รายการความเสี่ยง/โอกาส</b> list.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // The previous action's list stays mounted for a few frames while the
        // new one loads; wait for the target action's breadcrumb before
        // clicking "New" so the record is created in the right model.
        waitForAction('ความเสี่ยงและโอกาส'),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new risk/opportunity record."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='title'] input",
            content: _t("Enter the risk/opportunity title."),
            run: "edit Supply chain disruption risk",
        },
        {
            trigger: ".o_field_widget[name='risk_type'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>type</b>: Risk or Opportunity.")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='category'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>category</b> (Strategic, Operational, Financial, etc.).")),
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
            trigger: ".o_field_widget[name='risk_owner_id'] input",
            content: markup(_t("Set the <b>risk owner</b>.")),
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('รายละเอียด')",
            content: markup(_t("Open the <b>รายละเอียด (Details)</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='description'] textarea",
            content: _t("Describe the risk/opportunity."),
            run: "edit Key supplier may face production delays",
        },
        {
            trigger: ".o_field_widget[name='cause'] textarea",
            content: _t("Describe the cause."),
            run: "edit Single-source dependency on critical raw material",
        },
        {
            trigger: ".o_field_widget[name='consequence'] textarea",
            content: _t("Describe the consequence."),
            run: "edit Production halt and customer delivery delays",
        },
        ...stepUtils.saveForm(),

        // --- Risk Workflow ---
        {
            trigger: "button[name='action_identified']",
            content: markup(_t("Click <b>ระบุ</b> (Identify) to confirm the risk.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('วิเคราะห์และประเมิน')",
            content: markup(_t("Open the <b>วิเคราะห์และประเมิน (Analysis &amp; Evaluation)</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='likelihood'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>likelihood</b> (1-5).")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='severity'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>severity</b> (1-5). The risk score and level are calculated automatically.")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_analyzed']",
            content: markup(_t("Click <b>วิเคราะห์</b> (Analyze).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_evaluated']",
            content: markup(_t("Click <b>ประเมิน</b> (Evaluate).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('การดำเนินการ')",
            content: markup(_t("Open the <b>การดำเนินการ (Treatment)</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='treatment_type'] .o_select_menu_toggler",
            content: markup(_t("Set the <b>treatment type</b> (Avoid, Mitigate, Transfer, Accept).")),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='treatment_plan'] textarea",
            content: markup(_t("Describe the <b>treatment plan</b>.")),
            run: "edit Qualify alternative suppliers and maintain safety stock",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_treated']",
            content: markup(_t("Click <b>ดำเนินการ</b> (Treat).")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_monitored']",
            content: markup(_t("Click <b>เฝ้าดู</b> (Monitor) to put the risk under monitoring.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_close']",
            content: markup(_t("Click <b>ปิด</b> (Close) when the risk is resolved.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Risk &amp; Opportunity complete! Workflow: " +
                "<b>Draft → Identified → Analyzed → Evaluated → Treated → Monitored → Closed</b>. " +
                "Risk score = likelihood × severity, with automatic risk level (Low/Medium/High/Critical)."
            )),
            run: "click",
        },
    ],
});
