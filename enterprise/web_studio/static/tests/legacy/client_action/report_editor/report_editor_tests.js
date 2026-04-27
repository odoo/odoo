/** @odoo-module **/

import { Component, onWillRender, useState, xml } from "@odoo/owl";
import { getFixture, mount, click } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { ReportEditorModel } from "@web_studio/client_action/report_editor/report_editor_model";

QUnit.module("Report Editor", (hooks) => {
    let target;

    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.test("setting is in edition doesn't produce intempestive renders", async (assert) => {
        const fakeUIService = {
            start() {
                return {
                    block: () => assert.step("block"),
                    unblock: () => assert.step("unblock"),
                };
            },
        };

        registry.category("services").add("ui", fakeUIService);
        const env = await makeTestEnv();
        class Child extends Component {
            static template = xml`<div class="child" t-esc="props.rem.isInEdition"/>`;
            static props = ["*"];
            setup() {
                onWillRender(() => assert.step("Child rendered"));
            }
        }

        class Parent extends Component {
            static components = { Child };
            static template = xml`
                <Child rem="rem" />
                <button class="test-btn" t-on-click="() => rem.setInEdition(false)">btn</button>
            `;
            static props = ["*"];

            setup() {
                this.rem = useState(
                    new ReportEditorModel({ services: env.services, resModel: "partner" })
                );
                onWillRender(() => assert.step("Parent rendered"));
                this.rem.setInEdition(true);
            }
        }
        await mount(Parent, target, { env });
        assert.verifySteps(["block", "Parent rendered", "Child rendered"]);
        assert.strictEqual(target.querySelector(".child").textContent, "true");

        await click(target.querySelector("button.test-btn"));
        assert.strictEqual(target.querySelector(".child").textContent, "false");
        assert.verifySteps(["unblock", "Child rendered"]);
    });
});
