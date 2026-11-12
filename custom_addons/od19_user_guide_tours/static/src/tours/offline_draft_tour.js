import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Offline Draft Tour
 *
 * Introduces the "Offline Drafts / ร่างอัตโนมัติ" feature (od19_offline_draft):
 * forms are autosaved as drafts and can be restored later.
 *  1. Open Settings > Technical > Offline Drafts
 *  2. Review the stored drafts and their states
 *  3. Learn how a draft is restored from the form banner
 *
 * The menu lives under Settings > Technical and is restricted to the
 * administrator group (base.group_system, and Technical itself to
 * base.group_no_one), so every step that targets it is guarded with
 * `isActive`: a non-administrator simply skips those steps.
 */
registry.category("web_tour.tours").add("od19_offline_draft_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("มาดูระบบ <b>ร่างอัตโนมัติ (Offline Drafts)</b> ที่บันทึกร่างฟอร์มไว้ให้กู้คืนกัน"))
        ),

        // --- Settings > Technical > Offline Drafts (administrators only) ---
        {
            isActive: [navSection("Technical")],
            trigger: navSection("Technical"),
            content: markup(_t("เปิดเมนู <b>Technical</b> (สำหรับผู้ดูแลระบบ)")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: [navItem("Offline Drafts")],
            trigger: navItem("Offline Drafts"),
            content: markup(_t("เปิด <b>Offline Drafts</b> เพื่อดูรายการร่างที่บันทึกไว้")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            ...waitForAction("Offline Drafts / ร่างอัตโนมัติ"),
            isActive: [navSection("Technical")],
        },
        {
            isActive: [navSection("Technical")],
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ทุกแถวคือ <b>ร่างอัตโนมัติ</b> ของฟอร์มหนึ่ง ๆ: แสดงชื่อ (เช่น <b>sale.order#new</b>), " +
                "<b>โมเดล</b>, <b>ผู้ใช้</b>, <b>สถานะ</b> (Active / Applied / Discarded / Expired) " +
                "และ <b>วันหมดอายุ</b>"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: [navSection("Technical")],
            trigger: ".o_list_renderer",
            content: markup(_t(
                "ระบบบันทึกร่างอัตโนมัติระหว่างกรอกฟอร์ม (หน่วงประมาณ 2 วินาที) และเก็บไว้ 7 วัน — " +
                "เมื่อเปิดฟอร์มเดิมอีกครั้ง จะมีแบนเนอร์ <b>พบร่างที่บันทึกไว้</b> ให้กด <b>กู้คืน</b> หรือ <b>ทิ้ง</b>"
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer, .o_form_view, .o_kanban_view, .o_web_client",
            content: markup(_t(
                "จบการแนะนำ <b>ร่างอัตโนมัติ</b> แล้ว! ร่างที่บันทึกไว้จะกู้คืนได้จากแบนเนอร์ในฟอร์ม " +
                "(เมนูนี้เห็นเฉพาะผู้ดูแลระบบ)"
            )),
            run: "click",
        },
    ],
});
