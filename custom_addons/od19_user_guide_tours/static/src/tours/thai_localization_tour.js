import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Thai Localization Tour
 *
 * Introduces the Thai localization defaults shipped by
 * od19_thai_localization_base, exposed on Settings > General Settings:
 *  1. Open Settings > General Settings
 *  2. Go to the "Thai Localization" block
 *  3. Review the "Use Buddhist Year (พ.ศ.)" toggle (l10n_th_buddhist_year)
 *     and the company default font (Sarabun)
 */
registry.category("web_tour.tours").add("od19_thai_localization_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("มาดูการตั้งค่า <b>Thai Localization (การแปลท้องถิ่นไทย)</b> กัน"))
        ),

        // --- Settings > General Settings ---
        {
            trigger: navSection("General Settings"),
            content: markup(_t("เปิด <b>General Settings</b> (การตั้งค่าทั่วไป)")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_settings_container",
            content: markup(_t("เลื่อนลงไปยังส่วน <b>Thai Localization</b> ท้ายหน้าการตั้งค่าทั่วไป")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Thai Localization block ---
        {
            trigger: "h2:contains('Thai Localization')",
            content: markup(_t(
                "นี่คือส่วน <b>Thai Localization</b> ที่ OD19 เพิ่มไว้ให้ปรับค่าการใช้งานภาษาไทย " +
                "โดยเฉพาะ — ใช้กับรายงานและเอกสารภาษาไทยทั้งระบบ"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "#thai_buddhist_year_setting",
            content: markup(_t(
                "สวิตช์ <b>Use Buddhist Year (พ.ศ.)</b> (ฟิลด์ <b>l10n_th_buddhist_year</b>) " +
                "เมื่อเปิด วันที่ในรายงานภาษาไทยจะใช้ปีพุทธศักราช (เช่น 2568 แทน 2025) " +
                "และค่าเริ่มต้นของบริษัทคือ <b>เปิดใช้งาน</b>"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "#thai_buddhist_year_setting",
            content: markup(_t(
                "ฟอนต์เริ่มต้นของบริษัทถูกตั้งเป็น <b>Sarabun</b> ให้แล้ว เพื่อให้เอกสารและรายงาน " +
                "ภาษาไทยแสดงผลถูกต้อง — เปลี่ยนได้ที่การตั้งค่าฟอนต์ของบริษัท"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_settings_container",
            content: markup(_t(
                "จบการแนะนำ <b>Thai Localization</b> แล้ว! ปรับปีพุทธศักราชและฟอนต์ไทยได้ที่ " +
                "General Settings → Thai Localization"
            )),
            run: "click",
        },
    ],
});
