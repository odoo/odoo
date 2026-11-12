import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Project Document Sequence Tour
 *
 * Explains the department / salesperson based Job (project) numbering added by
 * od19_project_document_sequence:
 *  - od19_project_type ("Project Type"): Job / Preventive Maintenance /
 *    Service / Sales — picks the sequence prefix.
 *  - od19_sale_person_id ("Salesperson"): its initials are inserted before the
 *    2-digit year of the generated job number.
 *
 * Format examples:
 *  - Job         : JB (dept) + initials + 26 (year) + -0001  e.g. JBNV26-0001
 *  - PM          : PMB + initials + 26 + -0001               e.g. PMBNV26-0001
 *  - Service     : SB  + initials + 26 + -0001               e.g. SBNV26-0001
 *  - Sales       : S   + initials + 26 + -0001               e.g. SNV26-0001
 *
 * The two fields are injected before `user_id` in project.edit_project
 * (views/project_project_views.xml).
 *
 * App root menu xmlid used by this tour: `project.menu_main_pm`
 * (odoo/addons/project/views/project_menus.xml -> menuitem id="menu_main_pm").
 */
registry.category("web_tour.tours").add("od19_project_document_sequence_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "project.menu_main_pm",
            markup(_t("มาดูระบบ <b>ออกเลขงาน (Job No.) อัตโนมัติ</b> ตามแผนกและผู้ขาย/เซลส์ ในแอป <b>Project</b> กัน"))
        ),
        {
            trigger: navSection("Projects"),
            content: markup(_t("เปิดเมนู <b>Projects</b> เพื่อดูรายการโครงการทั้งหมด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_switch_view.o_list",
            content: markup(_t("สลับไปมุมมอง <b>List</b> เพื่อเปิดดูรายละเอียดโครงการได้ง่ายขึ้น")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "นี่คือรายการโครงการ — คอลัมน์ <b>Job No.</b> (เลขงาน) ถูกออกให้อัตโนมัติ " +
                "ตามประเภทโครงการ แผนก และอักษรย่อผู้ขาย/เซลส์ เปิดโครงการใดก็ได้เพื่อดูฟิลด์ที่ใช้กำหนด"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer .o_data_row:first td.o_data_cell[name='name']",
            content: markup(_t("เปิดโครงการแรกเพื่อดูรายละเอียด")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_project_type']",
            content: markup(_t(
                "<b>Project Type</b> — เลือกประเภทโครงการ: <b>Job</b> (JB/JT/JI/JD), " +
                "<b>Preventive Maintenance</b> (PMB/PMT/PMI/PMD), <b>Service</b> (SB/ST/SI/SD) " +
                "หรือ <b>Sales</b> (S) — เป็นตัวกำหนดคำนำหน้า (prefix) ของเลขงาน"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_sale_person_id']",
            content: markup(_t(
                "<b>Salesperson</b> — อักษรย่อ (Initials) ของผู้ขาย/เซลส์จะถูกแทรกก่อนปี 2 หลัก " +
                "ในเลขงาน เช่น อักษรย่อ <b>NV</b> รวมกับรหัสแผนก JB และปี 26 ได้เป็น <b>JBNV26-0001</b>"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "จบการแนะนำ <b>เลขงานอัตโนมัติ</b> แล้ว! รูปแบบคือ " +
                "<b>คำนำหน้าประเภท+แผนก</b> + <b>อักษรย่อผู้ขาย</b> + <b>ปี (2 หลัก)</b> + <b>เลขรัน</b> " +
                "เช่น JBNV26-0001 (Job), PMBNV26-0001 (PM), SBNV26-0001 (Service), SNV26-0001 (Sales)"
            )),
            run: "click",
        },
    ],
});
