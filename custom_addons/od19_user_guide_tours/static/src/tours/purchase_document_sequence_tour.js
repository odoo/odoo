import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Purchase Document Sequence Tour
 *
 * Explains the ISO-style document numbering per department added to Purchase
 * Orders by od19_purchase_document_sequence:
 *  - department_id     ("Department")    : selects the running sequence.
 *  - od19_purchase_type ("Purchase Type"): Local (PB/PT/PI/PF/PF-D),
 *    Indent/Import (IB/IT/II) or Bulk (BULK).
 *
 * The two fields are injected right after `partner_id` in
 * purchase.purchase_order_form (views/purchase_order_views.xml).
 */
registry.category("web_tour.tours").add("od19_purchase_document_sequence_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase.menu_purchase_root",
            markup(_t("มาดูระบบ <b>ออกเลขเอกสาร ISO แยกตามแผนก</b> ของใบสั่งซื้อ ในแอป <b>Purchase</b> กัน"))
        ),
        {
            trigger: navSection("Orders"),
            content: markup(_t("เปิดเมนู <b>Orders</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Purchase Orders"),
            content: markup(_t("เปิด <b>Purchase Orders</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Purchase Orders"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "นี่คือรายการใบสั่งซื้อ — คอลัมน์ <b>Reference</b> จะถูกออกให้อัตโนมัติ " +
                "โดยอ้างอิงจาก <b>แผนก</b> และ <b>ประเภทการจัดซื้อ</b> เปิดใบสั่งซื้อใดก็ได้เพื่อดูฟิลด์ที่ใช้กำหนด"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='name']",
            content: markup(_t("เปิดใบสั่งซื้อใบแรกเพื่อดูรายละเอียด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='department_id']",
            content: markup(_t(
                "<b>Department</b> — แผนกของใบสั่งซื้อ เป็นตัวเลือกลำดับเลข (Sequence) ที่จะใช้รัน " +
                "เช่น แผนก BA, TA, IA หรือ F/DES เพื่อให้ได้เลขเอกสารแยกตามแผนก"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_purchase_type']",
            content: markup(_t(
                "<b>Purchase Type</b> — ประเภทการจัดซื้อ: <b>Local</b> ใช้ชุด PB/PT/PI/PF, " +
                "<b>Indent/Import</b> ใช้ชุด IB/IT/II และ <b>Bulk</b> ใช้ชุด BULK " +
                "เป็นตัวกำหนดรูปแบบและคำนำหน้าของเลขเอกสาร"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>เลขเอกสารใบสั่งซื้อ</b> แล้ว! เลข Reference จะออกอัตโนมัติจาก " +
                "<b>แผนก + ประเภทการจัดซื้อ</b> (Local = PB/PT/PI/PF, Indent = IB/IT/II, Bulk = BULK) " +
                "แยกชุดเลขต่อแผนกเพื่อไม่ให้รหัสชนกัน"
            )),
            run: "click",
        },
    ],
});
