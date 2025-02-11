/** @odoo-module **/

import { start } from "@mail/../tests/helpers/test_utils";

QUnit.module("activity");

QUnit.test(
    "horizontal scroll applies only to the content, not to the whole controller",
    async (assert) => {
        const { openView } = await start();
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        const o_view_controller = document.querySelector(".o_view_controller");
        const o_content = o_view_controller.querySelector(".o_content");
        const o_cp_item = o_view_controller.querySelector(
            ".o_control_panel .o_breadcrumb .active"
        );
        const initialXCpItem = o_cp_item.getBoundingClientRect().x;
        const o_header_cell = o_content.querySelector(".o_activity_type_cell");
        const initialXHeaderCell = o_header_cell.getBoundingClientRect().x;
        assert.hasClass(o_view_controller, "o_action_delegate_scroll");
        assert.strictEqual(window.getComputedStyle(o_view_controller).overflow, "hidden");
        assert.strictEqual(window.getComputedStyle(o_content).overflow, "auto");
        assert.strictEqual(o_content.scrollLeft, 0);

        o_content.scrollLeft = 100;
        assert.strictEqual(o_content.scrollLeft, 100);
        assert.ok(o_header_cell.getBoundingClientRect().x < initialXHeaderCell);
        assert.strictEqual(o_cp_item.getBoundingClientRect().x, initialXCpItem);
    }
);
