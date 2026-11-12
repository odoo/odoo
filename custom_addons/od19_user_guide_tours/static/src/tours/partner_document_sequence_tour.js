import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Partner Document Sequence Tour
 *
 * Walks the user through the automatic partner reference numbering added by
 * od19_partner_document_sequence:
 *  - customer -> ir.sequence "res.partner"        -> C#### (Customer Master)
 *  - supplier -> ir.sequence "res.partner.vendor" -> V#### (Vendor Master)
 *  - is_auto_running toggles auto-numbering (turned off when the partner is
 *    both a customer and a vendor).
 *
 * The three fields are injected right after `ref` inside the "Sales & Purchase"
 * tab of the Contact form
 * (views/res_partner_views.xml -> base.view_partner_form).
 */
registry.category("web_tour.tours").add("od19_partner_document_sequence_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "contacts.menu_contacts",
            markup(_t("มาดูระบบ <b>ออกรหัสคู่ค้าอัตโนมัติ</b> (ลูกค้า C / ผู้ขาย V) ในแอป <b>Contacts</b> กัน"))
        ),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "นี่คือรายการคู่ค้าทั้งหมด — คอลัมน์ <b>Reference</b> คือรหัสที่ระบบออกให้อัตโนมัติ " +
                "เปิดคู่ค้ารายใดก็ได้เพื่อดูฟิลด์ที่ควบคุมการออกรหัส"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='complete_name']",
            content: markup(_t("เปิดคู่ค้ารายแรกเพื่อดูรายละเอียด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "a.nav-link:contains('Sales & Purchase')",
            content: markup(_t(
                "เปิดแท็บ <b>Sales &amp; Purchase</b> ซึ่งเป็นที่ตั้งของฟิลด์รหัสคู่ค้าและตัวควบคุมการออกรหัสอัตโนมัติ"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='ref']",
            content: markup(_t(
                "<b>Reference</b> — เลขรหัสคู่ค้าที่ระบบสร้างให้อัตโนมัติ " +
                "ลูกค้าเริ่มด้วย <b>C</b> และผู้ขายเริ่มด้วย <b>V</b> ตามด้วยเลขรัน 4 หลัก"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='customer']",
            content: markup(_t(
                "<b>Is a Customer</b> — เมื่อทำเครื่องหมาย ระบบจะออกรหัสลูกค้าเป็นรูปแบบ <b>C####</b> " +
                "(Customer Master)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='supplier']",
            content: markup(_t(
                "<b>Is a Vendor</b> — เมื่อทำเครื่องหมาย ระบบจะออกรหัสผู้ขายเป็นรูปแบบ <b>V####</b> " +
                "(Vendor Master)"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='is_auto_running']",
            content: markup(_t(
                "<b>Auto Running</b> — เปิด/ปิดการออกรหัสอัตโนมัติ " +
                "ถ้าคู่ค้าเป็นทั้งลูกค้าและผู้ขาย ระบบจะปิดให้อัตโนมัติเพื่อกันรหัสชนกัน"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>การออกรหัสคู่ค้า</b> แล้ว! ลูกค้าได้รหัส <b>C####</b> " +
                "และผู้ขายได้รหัส <b>V####</b> โดยอ้างอิงจากลำดับเลข (Sequence) ที่ตั้งไว้ในระบบ " +
                "ซึ่งผู้ดูแลระบบสามารถดูแลได้ที่ Settings → Technical → Sequences"
            )),
            run: "click",
        },
    ],
});
