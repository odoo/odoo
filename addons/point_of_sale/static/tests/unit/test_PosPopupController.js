/** @odoo-module */

import PosPopupController from "@point_of_sale/js/Popups/PosPopupController";
import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import PosComponent from "@point_of_sale/js/PosComponent";
import makeTestEnvironment from "web.test_env";
import testUtils from "web.test_utils";
import Registries from "@point_of_sale/js/Registries";
import { mount } from "@web/../tests/helpers/utils";

const { EventBus, useSubEnv, xml } = owl;

QUnit.module("unit tests for PosPopupController", {
    before() {
        Registries.Component.freeze();

        // Note that we are creating new popups here to decouple this test from the pos app.
        class CustomPopup1 extends AbstractAwaitablePopup {}
        CustomPopup1.template = xml/* html */ `
                <div class="popup custom-popup-1">
                    <footer>
                        <div class="confirm" t-on-click="confirm">
                            Yes
                        </div>
                        <div class="cancel" t-on-click="cancel">
                            No
                        </div>
                    </footer>
                </div>
            `;

        class CustomPopup2 extends AbstractAwaitablePopup {}
        CustomPopup2.template = xml/* html */ `
                <div class="popup custom-popup-2">
                    <footer>
                        <div class="confirm" t-on-click="confirm">
                            Okay
                        </div>
                    </footer>
                </div>
            `;

        PosPopupController.components = { CustomPopup1, CustomPopup2 };
    },
});

QUnit.test("allow multiple popups at the same time", async function (assert) {
    assert.expect(12);

    class Root extends PosComponent {
        setup() {
            super.setup();
            useSubEnv({
                isDebug: () => false,
                posbus: new EventBus(),
            });
        }
    }
    Root.env = makeTestEnvironment();
    Root.template = xml/* html */ `
            <div>
                <PosPopupController />
            </div>
        `;

    const root = await mount(Root, testUtils.prepareTarget());

    // Check 1 popup
    let popup1Promise = root.showPopup("CustomPopup1", {});
    await testUtils.nextTick();
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 1);
    testUtils.dom.click(root.el.querySelector(".modal-dialog .custom-popup-1 .confirm"));
    let result1 = await popup1Promise;
    assert.strictEqual(result1.confirmed, true);
    await testUtils.nextTick();
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 0);

    // Check multiple popups
    popup1Promise = root.showPopup("CustomPopup1", {});
    await testUtils.nextTick();

    // Check if the first popup is shown.
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 1);

    const popup2Promise = root.showPopup("CustomPopup2", {});
    await testUtils.nextTick();

    // Check for the second popup.
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 2);

    // popup 1 should be hidden
    assert.strictEqual(root.el.querySelectorAll(".modal-dialog.oe_hidden").length, 1);

    // click confirm on popup 2
    testUtils.dom.click(root.el.querySelector(".modal-dialog .custom-popup-2 .confirm"));
    await testUtils.nextTick();

    // after confirming on popup 2, only 1 should remain.
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 1);
    assert.strictEqual(root.el.querySelectorAll(".modal-dialog .custom-popup-2").length, 0);

    // popup 1 should not be hidden
    const CustomPopup1 = root.el.querySelector(".modal-dialog");
    assert.strictEqual(![...CustomPopup1.classList].includes("oe_hidden"), true);
    testUtils.dom.click(root.el.querySelector(".modal-dialog .custom-popup-1 .cancel"));
    await testUtils.nextTick();

    // after cancelling popup 1, no popup should remain.
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 0);

    result1 = await popup1Promise;
    const result2 = await popup2Promise;
    assert.strictEqual(result1.confirmed, false); // false because it's cancelled.
    assert.strictEqual(result2.confirmed, true); // true because it's confirmed.
});

QUnit.test("pressing cancel/confirm key should only close the top popup", async function (assert) {
    assert.expect(6);

    class Root extends PosComponent {
        setup() {
            super.setup();
            useSubEnv({
                isDebug: () => false,
                posbus: new EventBus(),
            });
        }
    }
    Root.env = makeTestEnvironment();
    Root.template = xml/* html */ `
            <div>
                <PosPopupController />
            </div>
        `;

    const root = await mount(Root, testUtils.prepareTarget());

    const popup1Promise = root.showPopup("CustomPopup1", {
        confirmKey: "Enter",
        cancelKey: "Escape",
    });
    await testUtils.nextTick();
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 1);

    const popup2Promise = root.showPopup("CustomPopup2", {
        confirmKey: "Enter",
        cancelKey: "Escape",
    });
    await testUtils.nextTick();
    assert.strictEqual(root.el.querySelectorAll(".popup").length, 2);

    // Pressing 'Escape' should cancel the top popup which is the CustomPopup2.
    testUtils.dom.triggerEvent(window, "keyup", { key: "Escape" });
    await testUtils.nextTick();

    // Therefore, the popup2Promise has now resolved with `confirmed` value = false.
    const result2 = await popup2Promise;
    assert.strictEqual(result2.confirmed, false);

    assert.strictEqual(root.el.querySelectorAll(".popup").length, 1);

    testUtils.dom.triggerEvent(window, "keyup", { key: "Enter" });
    await testUtils.nextTick();

    assert.strictEqual(root.el.querySelectorAll(".popup").length, 0);

    const result1 = await popup1Promise;
    assert.strictEqual(result1.confirmed, true);
});
