/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { click, getFixture, mount, nextTick, triggerEvent } from "@web/../tests/helpers/utils";
import { clearRegistryWithCleanup, makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { popupService } from "@point_of_sale/app/popup/popup_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";

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

class Root extends Component {
    static components = { MainComponentsContainer };
    setup() {
        this.popup = useService("popup");
    }
}
Root.template = xml`<MainComponentsContainer/>`;

let env;
QUnit.module("unit tests for PopupContainer", {
    async beforeEach() {
        const makeService = (obj) => ({
            start() {
                return obj;
            },
        });
        registry.category("services").add("popup", popupService);
        registry.category("services").add("pos_notification", makeService({ add() {} }));
        registry.category("services").add("sound", makeService({ play() {} }));
        registry.category("services").add("pos", makeService({}));
        clearRegistryWithCleanup(registry.category("main_components"));
        env = await makeTestEnv();
    },
});

QUnit.test("allow multiple popups at the same time", async function (assert) {
    const fixture = getFixture();
    const root = await mount(Root, fixture, { env });

    // Single popup
    let popup1Promise = root.popup.add(CustomPopup1, {});
    await nextTick();
    assert.containsOnce(fixture, ".popup", "popup is open");
    await click(fixture.querySelector(".modal-dialog .custom-popup-1 .confirm"));
    let result1 = await popup1Promise;
    assert.strictEqual(result1.confirmed, true, "popup is confirmed");
    assert.containsNone(fixture, ".popup", 0, "popup is closed");

    // Multiple popups
    popup1Promise = root.popup.add(CustomPopup1, {});
    await nextTick();

    assert.containsOnce(fixture, ".popup", 1, "first popup is shown");

    const popup2Promise = root.popup.add(CustomPopup2, {});
    await nextTick();

    assert.containsOnce(fixture, ".popup", "only one popup is displayed");
    assert.containsOnce(fixture, ".custom-popup-2", "second popup is displayed");
    assert.containsNone(fixture, ".custom-popup-1", "first popup is not displayed");

    await click(fixture.querySelector(".modal-dialog .custom-popup-2 .confirm"));

    assert.containsOnce(fixture, ".popup", "after confirming on popup 2, only 1 should remain");
    assert.containsOnce(fixture, ".custom-popup-1", "first popup is displayed");
    assert.containsNone(fixture, ".custom-popup-2", "second popup is closed");

    await click(fixture.querySelector(".modal-dialog .custom-popup-1 .cancel"));

    assert.containsNone(fixture, ".popup", "after cancelling popup 1, no popup should remain.");

    result1 = await popup1Promise;
    const result2 = await popup2Promise;
    assert.strictEqual(result1.confirmed, false, "popup 1 is not confirmed");
    assert.strictEqual(result2.confirmed, true, "popup 2 is confirmed");
});

QUnit.test("pressing cancel/confirm key should only close the top popup", async function (assert) {
    const fixture = getFixture();
    const root = await mount(Root, fixture, { env });

    const popup1Promise = root.popup.add(CustomPopup1, {
        confirmKey: "Enter",
        cancelKey: "Escape",
    });
    await nextTick();
    assert.containsOnce(fixture, ".custom-popup-1", "first popup is open");

    const popup2Promise = root.popup.add(CustomPopup2, {
        confirmKey: "Enter",
        cancelKey: "Escape",
    });
    await nextTick();
    assert.containsNone(fixture, ".custom-popup-1", "first popup no longer displayed");
    assert.containsOnce(fixture, ".custom-popup-2", "second popup is open");

    await triggerEvent(fixture, ".popup", "keyup", { key: "Escape" });
    assert.containsNone(fixture, ".custom-popup-2", "second popup no longer displayed");
    assert.containsOnce(fixture, ".custom-popup-1", "first popup is displayed again");

    const result2 = await popup2Promise;
    assert.strictEqual(
        result2.confirmed,
        false,
        "canceling the popup with escape resolved the promise with confirmed: false"
    );

    await triggerEvent(fixture, ".popup", "keyup", { key: "Enter" });
    assert.containsNone(fixture, ".popup", "no popups remain");

    const result1 = await popup1Promise;
    assert.strictEqual(
        result1.confirmed,
        true,
        "confirming the popup with enter resolved the promise with confirmed: true"
    );
});
