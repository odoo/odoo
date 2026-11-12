import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 User Guide Tour
 *
 * Introduces the "User Guide" application: the user-facing hub from which every
 * interactive tour of the OD19 business modules can be browsed and started.
 *  1. Open the "User Guide" app (root menu menu_od19_user_guide_root)
 *  2. Open the "Interactive Tours" submenu
 *  3. Review the tour list (Tours) and how to start a tour
 */
registry.category("web_tour.tours").add("od19_user_guide_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_user_guide_tours.menu_od19_user_guide_root",
            markup(_t("ยินดีต้อนรับสู่แอป <b>User Guide</b> (คู่มือผู้ใช้) — ที่นี่คือศูนย์รวมทัวร์แนะนำการใช้งานทั้งหมด"))
        ),

        // --- Interactive Tours submenu ---
        {
            trigger: navSection("Interactive Tours"),
            content: markup(_t("เปิดเมนูย่อย <b>Interactive Tours</b> เพื่อดูรายการทัวร์แนะนำที่มีให้ใช้งาน")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Tours"),

        // --- Tour list ---
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ทุกแถวในลิสต์ <b>Tours</b> คือหนึ่งทัวร์แนะนำ: คอลัมน์ <b>Name</b> คือชื่อทัวร์ " +
                "และคอลัมน์ <b>URL</b> คือจุดเริ่มต้นที่ทัวร์จะพาไป"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "เริ่มทัวร์ได้โดยกดปุ่ม <b>Onboarding</b> ท้ายแถวของทัวร์ที่ต้องการ " +
                "(ปุ่ม <b>Testing</b> สงวนไว้สำหรับนักพัฒนา) ทัวร์จะพาไปทีละขั้นตอนพร้อมคำอธิบาย"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer, .o_kanban_view, .o_form_view",
            content: markup(_t(
                "จบการแนะนำ <b>User Guide</b> แล้ว! เลือกทัวร์ที่ต้องการแล้วกด <b>Onboarding</b> " +
                "เพื่อเริ่มเรียนรู้การใช้งานทีละขั้นตอน"
            )),
            run: "click",
        },
    ],
});
