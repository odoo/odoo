import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Quotation Document Sequence Tour
 *
 * Explains the department-based quotation numbering and quotation revision
 * added by od19_quotation_document_sequence:
 *  - department_id ("Department") picks the per-department sequence:
 *    QB (BA), QT (TA), QI (IA), QD (F/DES) + YY + MM + running number.
 *  - "Create Revision" (action_create_revision) creates a new revision of the
 *    quotation, "Revisions" (action_view_revisions) lists the revision chain.
 *
 * The field/buttons come from views/sale_order_views.xml (inherit
 * sale.view_order_form).
 */
registry.category("web_tour.tours").add("od19_quotation_document_sequence_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("มาดูระบบ <b>ออกเลขใบเสนอราคาแยกตามแผนก</b> (QB/QT/QI/QD) และ <b>การทำ Revision</b> ในแอป <b>Sales</b> กัน"))
        ),
        {
            trigger: navSection("Orders"),
            content: markup(_t("เปิดเมนู <b>Orders</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Quotations"),
            content: markup(_t("เปิดรายการ <b>Quotations</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Quotations"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "นี่คือรายการใบเสนอราคา — เลขเอกสาร (Number) จะถูกออกให้อัตโนมัติ " +
                "ตาม <b>แผนก</b> เปิดใบเสนอราคาใดก็ได้เพื่อดูรายละเอียด"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='name']",
            content: markup(_t("เปิดใบเสนอราคาใบแรกเพื่อดูรายละเอียด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='department_id']",
            content: markup(_t(
                "<b>Department</b> — แผนกของใบเสนอราคา เป็นตัวเลือกลำดับเลข (Sequence) ที่จะใช้รัน " +
                "โดยรูปแบบคือ <b>รหัสแผนก + ปี (2 หลัก) + เดือน (2 หลัก) + เลขรัน</b> " +
                "เช่น <b>QB</b> (BA), <b>QT</b> (TA), <b>QI</b> (IA), <b>QD</b> (F/DES)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["button[name='action_create_revision']"],
            trigger: "button[name='action_create_revision']",
            content: markup(_t(
                "<b>Create Revision</b> — สร้างใบเสนอราคาเวอร์ชันใหม่ (ใช้ได้ในสถานะ ฉบับร่าง/ส่งแล้ว) " +
                "ระบบจะสร้างเอกสารใหม่พร้อมสายการแก้ไข (Revision Chain)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["button[name='action_view_revisions']"],
            trigger: "button[name='action_view_revisions']",
            content: markup(_t(
                "<b>Revisions</b> — ดูรายการเวอร์ชันก่อนหน้าทั้งหมดของใบเสนอราคานี้ " +
                "(ปุ่มจะแสดงเมื่อมีเวอร์ชันเดิมอยู่แล้วเท่านั้น)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>เลขใบเสนอราคาและ Revision</b> แล้ว! เลขจะออกอัตโนมัติตาม <b>แผนก</b> " +
                "(QB/QT/QI/QD + ปี + เดือน + เลขรัน) และใช้ <b>Create Revision</b> / <b>Revisions</b> " +
                "เพื่อแก้ไขใบเสนอราคาโดยเก็บประวัติเวอร์ชันเดิมไว้"
            )),
            run: "click",
        },
    ],
});
