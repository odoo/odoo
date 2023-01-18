/** @odoo-module **/

import { start } from "@mail/../tests/helpers/test_utils";
import { prepareTarget } from "web.test_utils";

QUnit.module("test_mail", () => {
QUnit.module("activity view mobile");

QUnit.test('horizontal scroll applies only to the content, not to the whole controller', async (assert) => {
    const viewPort = prepareTarget();
    viewPort.style.position = "initial";
    viewPort.style.width = "initial";

    const { openView } = await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    const o_view_controller = document.querySelector(".o_view_controller");
    const o_content = o_view_controller.querySelector(".o_content");

    const o_cp_buttons = o_view_controller.querySelector(".o_control_panel .o_cp_buttons");
    const initialXCpBtn = o_cp_buttons.getBoundingClientRect().x;

    const o_header_cell = o_content.querySelector(".o_activity_type_cell");
    const initialXHeaderCell = o_header_cell.getBoundingClientRect().x;

    assert.hasClass(o_view_controller, "o_action_delegate_scroll",
        "the 'o_view_controller' should be have the 'o_action_delegate_scroll'.");
    assert.strictEqual(window.getComputedStyle(o_view_controller).overflow,"hidden",
        "the view controller should have overflow hidden");
    assert.strictEqual(window.getComputedStyle(o_content).overflow,"auto",
        "the view content should have the overflow auto");
    assert.strictEqual(o_content.scrollLeft, 0, "the o_content should not have scroll value");

    // Horizontal scroll
    o_content.scrollLeft = 100;

    assert.strictEqual(o_content.scrollLeft, 100, "the o_content should be 100 due to the overflow auto");
    assert.ok(o_header_cell.getBoundingClientRect().x < initialXHeaderCell,
        "the gantt header cell x position value should be lower after the scroll");
    assert.strictEqual(o_cp_buttons.getBoundingClientRect().x, initialXCpBtn,
        "the btn x position of the control panel button should be the same after the scroll");
    viewPort.style.position = "";
    viewPort.style.width = "";
});

});
