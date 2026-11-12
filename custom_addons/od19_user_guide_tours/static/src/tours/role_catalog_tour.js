import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Role Catalog Tour
 *
 * Introduces the OD19 business-role catalog (od19_role_catalog): the ~44
 * predefined ``res.users.role`` records grouped under the "OD19 Roles"
 * privilege and organised into families (Governance/IT, Sales, Purchase,
 * Inventory, Accounting, Service, HR, ISO, Reporting, Support).
 *  1. Open Settings > Users & Companies > User Roles
 *  2. Review the catalog list (name + default flag + user count)
 *  3. Inspect a role's "Groups" tab (the security groups it implies)
 */
registry.category("web_tour.tours").add("od19_role_catalog_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("มาดู <b>คลังบทบาทธุรกิจ (Role Catalog)</b> ที่ OD19 จัดเตรียมไว้กัน"))
        ),

        // --- Settings > Users & Companies > User Roles ---
        {
            trigger: navSection("Users & Companies"),
            content: markup(_t("เปิดเมนู <b>Users & Companies</b>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("User Roles"),
            content: markup(_t("เปิด <b>User Roles</b> เพื่อดูคลังบทบาทธุรกิจทั้งหมด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("User Roles"),

        // --- Role catalog ---
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "นี่คือ <b>คลังบทบาทธุรกิจของ OD19</b> (ประมาณ 44 บทบาท) ที่จัดกลุ่มตามครอบครัวงาน: " +
                "<b>Governance/IT, Sales, Purchase, คลังสินค้า, บัญชี/การเงิน, บริการหลังการขาย, " +
                "บุคคล, ISO/คุณภาพ/ความเสี่ยง, รายงาน และสนับสนุน</b>"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='name']",
            content: markup(_t(
                "ตัวอย่างบทบาท เช่น <b>ผู้จัดการระบบ</b>, <b>พนักงานขาย</b>, <b>เจ้าหน้าที่คลัง</b>, " +
                "<b>นักบัญชี</b>, <b>เจ้าหน้าที่บุคคล</b> — เปิดบทบาทแรกเพื่อดูรายละเอียด"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Role form: implied groups ---
        {
            trigger: ".o_field_widget[name='name']",
            content: markup(_t(
                "แต่ละบทบาทมี <b>ชื่อ</b> และตั้งค่า <b>is_default</b> ได้ — บทบาทที่ตั้งเป็นค่าเริ่มต้น " +
                "(เช่น <b>พนักงานทั่วไป</b>) จะถูกมอบให้ผู้ใช้ใหม่โดยอัตโนมัติ"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='implied_ids']",
            content: markup(_t(
                "แท็บ <b>Groups</b> แสดงกลุ่มความปลอดภัยที่บทบาทนี้ <b>imply</b> ให้อัตโนมัติ " +
                "เมื่อมอบบทบาทให้ผู้ใช้ ระบบจะให้สิทธิ์ตามกลุ่มเหล่านี้ทันที"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>คลังบทบาทธุรกิจ</b> แล้ว! บริหารบทบาททั้งหมดได้ที่ " +
                "Users & Companies → User Roles โดยแต่ละบทบาทผูกกลุ่มความปลอดภัยไว้ให้แล้ว"
            )),
            run: "click",
        },
    ],
});
