/** @odoo-module */

import NumberBuffer from "@point_of_sale/js/Misc/NumberBuffer";
import makeTestEnvironment from "web.test_env";
import testUtils from "web.test_utils";
import { mount } from "@web/../tests/helpers/utils";
import { LegacyComponent } from "@web/legacy/legacy_component";

const { useState, xml } = owl;

QUnit.module("unit tests for NumberBuffer", {
    before() {},
});

QUnit.test("simple fast inputs with capture in between", async function (assert) {
    assert.expect(3);
    const target = testUtils.prepareTarget();
    const env = makeTestEnvironment();

    class Root extends LegacyComponent {
        setup() {
            this.state = useState({ buffer: "" });
            NumberBuffer.activate();
            NumberBuffer.use({
                nonKeyboardInputEvent: "numpad-click-input",
                state: this.state,
            });
        }
        resetBuffer() {
            NumberBuffer.capture();
            NumberBuffer.reset();
        }
        onClickOne() {
            this.trigger("numpad-click-input", { key: "1" });
        }
        onClickTwo() {
            this.trigger("numpad-click-input", { key: "2" });
        }
    }
    Root.template = xml/* html */ `
            <div>
                <p><t t-esc="state.buffer" /></p>
                <button class="one" t-on-click="onClickOne">1</button>
                <button class="two" t-on-click="onClickTwo">2</button>
                <button class="reset" t-on-click="resetBuffer">reset</button>
            </div>
        `;

    await mount(Root, target, { env });

    const oneButton = target.querySelector("button.one");
    const twoButton = target.querySelector("button.two");
    const resetButton = target.querySelector("button.reset");
    const bufferEl = target.querySelector("p");

    testUtils.dom.click(oneButton);
    testUtils.dom.click(twoButton);
    await testUtils.nextTick();
    assert.strictEqual(bufferEl.textContent, "12");
    testUtils.dom.click(resetButton);
    await testUtils.nextTick();
    assert.strictEqual(bufferEl.textContent, "");
    testUtils.dom.click(twoButton);
    testUtils.dom.click(oneButton);
    await testUtils.nextTick();
    assert.strictEqual(bufferEl.textContent, "21");
});
