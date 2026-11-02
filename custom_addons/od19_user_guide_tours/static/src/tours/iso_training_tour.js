import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 ISO Training & Competence Tour
 *
 * Walks the user through:
 *  1. Creating a training course
 *  2. Course workflow: Draft → Planned → In Progress → Completed
 *  3. Managing competences and employee competence matrix
 */
registry.category("web_tour.tours").add("od19_iso_training_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_iso_document_control.menu_iso_root",
            markup(_t("Let's manage <b>Training &amp; Competence</b> for ISO compliance."))
        ),

        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('การฝึกอบรมและความสามารถ')",
            content: markup(_t("Open the <b>การฝึกอบรมและความสามารถ (Training &amp; Competence)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('หลักสูตรการฝึกอบรม'),
            content: markup(_t("Open <b>หลักสูตรการฝึกอบรม (Training Courses)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // The action switch is asynchronous; wait for the target list before
        // clicking "New" so the record lands in the right model.
        waitForAction('หลักสูตรการฝึกอบรม'),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new training course."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the course name."),
            run: "edit ISO 9001 Internal Auditor Training",
        },
        {
            trigger: ".o_field_widget[name='date'] .o_input",
            content: _t("Set the course date."),
            run: "edit 2026-05-20",
        },
        ...stepUtils.saveForm(),

        // --- Course Workflow ---
        {
            trigger: "button[name='action_plan']",
            content: markup(_t("Click <b>วางแปรยัง</b> (Plan) to confirm the course schedule.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_start']",
            content: markup(_t("Click <b>เริ่มจัดฝึก</b> (Start) when the training begins.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_complete']",
            content: markup(_t("Click <b>จบหลักสูตร</b> (Complete) when the training is finished.")),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Competences ---
        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('การฝึกอบรมและความสามารถ')",
            content: markup(_t("Open the <b>การฝึกอบรมและความสามารถ (Training &amp; Competence)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('ความสามารถ/ทักษะ'),
            content: markup(_t("Open <b>ความสามารถ/ทักษะ (Competences)</b> to define required skills.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction('ความสามารถ/ทักษะ'),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new competence/skill."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the competence name."),
            run: "edit Internal Auditing",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Employee Competence Matrix ---
        {
            trigger: navSection('การจัดการ ISO'),
            content: markup(_t("Open the <b>การจัดการ ISO</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('การฝึกอบรมและความสามารถ')",
            content: markup(_t("Open the <b>การฝึกอบรมและความสามารถ (Training &amp; Competence)</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('ตารางความสามารถพนักงาน'),
            content: markup(_t("Open <b>ตารางความสามารถพนักงาน (Employee Competence Matrix)</b> to assign competences to employees.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction('ตารางความสามารถพนักงาน'),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Training &amp; Competence complete! Course workflow: " +
                "<b>Draft → Planned → In Progress → Completed</b>. " +
                "Define competences, then assign them to employees via the competence matrix."
            )),
            run: "click",
        },
    ],
});
