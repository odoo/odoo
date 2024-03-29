/** @odoo-module */

import testUtils from "@web/../tests/legacy/helpers/test_utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, mount } from "@web/../tests/helpers/utils";
import { useService } from "@web/core/utils/hooks";
import { numberBufferService } from "@point_of_sale/app/utils/number_buffer_service";
import { registry } from "@web/core/registry";

import { Component, useState, xml } from "@odoo/owl";

QUnit.module("unit tests for NumberBuffer", {
    async beforeEach() {
        registry.category("services").add("number_buffer", numberBufferService);
        registry.category("services").add("sound", { start: () => ({ play() {} }) });
    },
});

QUnit.test("simple fast inputs with capture in between", async function (assert) {
    assert.expect(3);
    const target = getFixture();
    const env = await makeTestEnv();

    class Root extends Component {
        setup() {
            this.state = useState({ buffer: "" });
            this.numberBuffer = useService("number_buffer");
            this.numberBuffer.use({
                state: this.state,
            });
        }
        resetBuffer() {
            this.numberBuffer.capture();
            this.numberBuffer.reset();
        }
        onClickOne() {
            this.numberBuffer.sendKey("1");
        }
        onClickTwo() {
            this.numberBuffer.sendKey("2");
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
