import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales OCA Bridge Tour
 *
 * Explains the OCA "Required Now" bridge that
 * od19_sales_oca_bridge_workflow adds on the sale order form:
 *  1. Open the Sales app → Orders → Quotations and open any quotation.
 *  2. Switch to the "Other Info" tab that carries the
 *     "OCA Bridge (Required Now)" separator and its fields:
 *       - delivery_status      (OCA delivery state)
 *       - current_revision_id  (OCA sale order revision)
 *       - main_exception_id / exceptions_summary (OCA sale exception)
 *       - blanket_order_id     (OCA blanket order)
 *  3. Point out that approval thresholds are configured per company in
 *     Settings → Companies.
 */
registry.category("web_tour.tours").add("od19_sales_oca_bridge_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("มาเรียนรู้ <b>สะพานเชื่อม OCA</b> ที่เพิ่มอยู่บนใบสั่งขายกัน"))
        ),

        // --- Sales → Orders → Quotations ---
        {
            trigger: navSection("Orders"),
            content: markup(_t("เปิดเมนู <b>Orders</b> ในแอป Sales")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Quotations"),
            content: markup(_t("เลือก <b>Quotations</b> เพื่อเปิดรายการใบเสนอราคา")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Quotations"),
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("เปิดใบเสนอราคาใดก็ได้หนึ่งรายการ")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- OCA Bridge (Required Now) on the "Other Info" tab ---
        {
            trigger: ".o_notebook .nav-link:contains('Other Info')",
            content: markup(_t(
                "ฟิลด์ของ OCA Bridge อยู่ในแท็บ <b>Other Info</b> เปิดแท็บนี้เพื่อดูข้อมูลเชื่อมโยง"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='delivery_status']",
            content: markup(_t(
                "ในกลุ่ม <b>OCA Bridge (Required Now)</b> ฟิลด์ <b>Delivery Status</b> แสดงสถานะการส่งมอบ " +
                "ที่เชื่อมมาจากความสามารถของ OCA delivery-state"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='current_revision_id']",
            content: markup(_t(
                "<b>Current Revision</b> แสดง revision ปัจจุบันของใบสั่งขาย (จาก OCA sale order revision)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='main_exception_id']",
            content: markup(_t(
                "<b>Main Exception</b> แสดงข้อยกเว้นหลักที่ระบบตรวจพบบนใบสั่งขาย (จาก OCA sale exception)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='exceptions_summary']",
            content: markup(_t(
                "<b>Exceptions Summary</b> สรุปข้อยกเว้นทั้งหมดที่อาจบล็อกการยืนยันคำสั่งขาย"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='blanket_order_id']",
            content: markup(_t(
                "<b>Blanket Order</b> อ้างถึงคำสั่งซื้อ/สัญญาแบบเหมาที่ใบสั่งขายนี้อ้างอิง (จาก OCA blanket order)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "ส่วน <b>การอนุมัติ</b>: วงเงินอนุมัติถูกกำหนด <b>ต่อบริษัท</b> ใน Settings → Companies " +
                "(<b>Sale Order Manager Approval Threshold</b> และ <b>Sale Order Director Approval Threshold</b>) " +
                "ใบสั่งขายที่ยอดถึงวงเงินจะเข้าสถานะ <b>Waiting Approval</b> ก่อนจึงจะยืนยันได้"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>OCA Bridge</b> แล้ว! ใบสั่งขายมีฟิลด์เชื่อมสถานะการส่งมอบ, revision, ข้อยกเว้น " +
                "และคำสั่งซื้อแบบเหมา ส่วนวงเงินอนุมัติตั้งค่าได้ที่ Settings → Companies"
            )),
            run: "click",
        },
    ],
});
