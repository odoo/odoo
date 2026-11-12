import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Timesheet Billing Tour
 *
 * Walks the user through billing delivered time into an invoice
 * (od19_project_timesheet_billing):
 *  1. Open the "Invoice Timesheets" wizard from the Sales app
 *     (Sales → section "To Invoice" → "Invoice Timesheets",
 *     xmlid menu_od19_timesheet_invoice_wizard) and review it.
 *  2. Narrate the "Unbilled Timesheets" stat button added on the project form
 *     (action_od19_view_unbilled_timesheets), shown only when the project has
 *     billable, not-yet-invoiced timesheets — hence the isActive guard.
 *
 * The sale order form also exposes the matching "Unbilled Timesheets" stat
 * button plus an "Invoice Timesheets" button
 * (action_od19_open_timesheet_invoice_wizard).
 */
registry.category("web_tour.tours").add("od19_timesheet_billing_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("มาเรียนรู้การ <b>เรียกเก็บเงินจาก Timesheet</b> กัน"))
        ),

        // --- Sales → To Invoice → Invoice Timesheets wizard ---
        {
            trigger: navSection("To Invoice"),
            content: markup(_t("เปิดเมนู <b>To Invoice</b> (ออกใบแจ้งหนี้) ในแอป Sales")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Invoice Timesheets"),
            content: markup(_t(
                "เปิด <b>Invoice Timesheets</b> เพื่อเรียกเก็บ Timesheet ที่ยังไม่ถูกออกใบแจ้งหนี้"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name='sale_order_ids']",
            content: markup(_t(
                "นี่คือวิซาร์ด <b>Invoice Timesheets</b> — เลือก <b>ใบสั่งขาย (Sales Orders)</b> ที่ยืนยันแล้ว " +
                "ที่ต้องการเรียกเก็บ ระบบจะดึงเฉพาะ Timesheet ที่ผูกกับรายการขายแบบ " +
                "&quot;เรียกเก็บตามเวลาที่ใช้&quot; และยังไม่ออกใบแจ้งหนี้"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name='date_start']",
            content: markup(_t(
                "กำหนด <b>วันเริ่มต้น (Start Date)</b> เพื่อจำกัดเฉพาะ Timesheet ในช่วงที่ต้องการ (เว้นว่าง = ทั้งหมด)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name='date_end']",
            content: markup(_t("กำหนด <b>วันสิ้นสุด (End Date)</b> ให้ครบช่วงวันที่ที่ต้องการเรียกเก็บ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal button[name='action_create_invoices']",
            content: markup(_t(
                "กด <b>Create Invoices</b> เพื่อสร้างใบแจ้งหนี้จาก Timesheet ที่เลือกโดยอัตโนมัติ " +
                "(หรือกด <b>Cancel</b> เพื่อปิดโดยไม่ทำอะไร)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn-secondary",
            content: markup(_t("ปิดวิซาร์ดด้วยปุ่ม <b>Cancel</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Project form: "Unbilled Timesheets" stat button ---
        ...stepUtils.goToAppSteps(
            "project.menu_main_pm",
            markup(_t("ต่อไปไปดู <b>ปุ่มสถิติ</b> ที่อยู่บนฟอร์มโครงการ"))
        ),
        {
            trigger: navSection("Projects"),
            content: markup(_t("เปิดเมนู <b>Projects</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Projects"),
        {
            trigger: ".o_switch_view.o_list",
            content: markup(_t("สลับไปมุมมอง <b>List</b> แล้วเปิดโครงการที่ต้องการ")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='name']",
            content: markup(_t("เปิดโครงการแรก")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["button[name='action_od19_view_unbilled_timesheets']"],
            trigger: "button[name='action_od19_view_unbilled_timesheets']",
            content: markup(_t(
                "ปุ่มสถิติ <b>Unbilled Timesheets</b> บนฟอร์มโครงการจะแสดงเมื่อมี Timesheet ที่ยังไม่ถูกเรียกเก็บ " +
                "กดเพื่อดูรายการเหล่านั้น (และบน <b>ใบสั่งขาย</b> ที่ยืนยันแล้ว จะมีปุ่ม <b>Unbilled Timesheets</b> " +
                "คู่กับปุ่ม <b>Invoice Timesheets</b> สำหรับเปิดวิซาร์ดในหน้าเดียว)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>การเรียกเก็บเงินจาก Timesheet</b> แล้ว! ใช้ <b>To Invoice → Invoice Timesheets</b> " +
                "เพื่อรวม Timesheet เป็นใบแจ้งหนี้ หรือดูจำนวนที่ยังไม่เรียกเก็บจากปุ่มสถิติ <b>Unbilled Timesheets</b>"
            )),
            run: "click",
        },
    ],
});
