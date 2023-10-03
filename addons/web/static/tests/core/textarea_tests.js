/** @odoo-module **/

import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, mount, triggerEvent, nextTick, editInput } from "@web/../tests/helpers/utils";

import { Component, useState, xml } from "@odoo/owl";
import { Textarea } from "@web/core/textarea/textarea";
import { Deferred } from "@web/core/utils/concurrency";
const serviceRegistry = registry.category("services");

let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.module("Textarea");

    QUnit.test("can be rendered", async (assert) => {
        const env = await makeTestEnv();
        await mount(Textarea, target, { env, props: { onChange: () => {} } });
        assert.containsOnce(target, 'textarea[class="o_input"]');
        assert.strictEqual(target.querySelector("textarea").value, "");
    });

    QUnit.test("can be rendered with a given value", async (assert) => {
        const env = await makeTestEnv();
        await mount(Textarea, target, { env, props: { value: "foo", onChange: () => {} } });
        assert.strictEqual(target.querySelector("textarea").value, "foo");
    });

    QUnit.test("can be rendered with a custom class name and id", async (assert) => {
        const env = await makeTestEnv();
        await mount(Textarea, target, {
            env,
            props: { className: "custom", id: "myId", onChange: () => {} },
        });
        assert.hasClass(target.querySelector("textarea"), "custom");
        assert.strictEqual(target.querySelector("textarea").id, "myId");
    });

    QUnit.test("call onChange prop when some change occurs", async (assert) => {
        const env = await makeTestEnv();

        let value = false;
        class Parent extends Component {
            onChange(val) {
                value = val;
            }
        }
        Parent.template = xml`<Textarea onChange="onChange"/>`;
        Parent.components = { Textarea };

        await mount(Parent, target, { env });
        assert.containsOnce(target, "textarea");
        await editInput(target, "textarea", "foo");
        assert.strictEqual(value, "foo");
        await editInput(target, "textarea", "bar");
        assert.strictEqual(value, "bar");
    });

    QUnit.test("can confirm value by pressing ENTER", async (assert) => {
        const env = await makeTestEnv();
        let value;
        class Parent extends Component {
            onChange(val) {
                value = val;
            }
        }
        Parent.template = xml`<Textarea onChange.bind="onChange"/>`;
        Parent.components = { Textarea };

        await mount(Parent, target, { env });
        assert.containsOnce(target, "textarea");
        target.querySelector("textarea").value = "foo";
        await triggerEvent(target, "textarea", "keydown", { key: "Enter" });
        assert.strictEqual(value, "foo");
    });

    QUnit.test("Do not update the textarea with props while editing", async (assert) => {
        const env = await makeTestEnv();
        const def = new Deferred();
        const def2 = new Deferred();
        class Parent extends Component {
            setup() {
                this.state = useState({ value: "" });
                def.then(() => {
                    this.state.value = "foo";
                });
                def2.then(() => {
                    this.state.value = "bar";
                });
            }

            onChange(val) {
                this.state.value = val;
            }
        }
        Parent.template = xml`<Textarea className="'custom'" onChange.bind="onChange" value="state.value"/>`;
        Parent.components = { Textarea };

        await mount(Parent, target, { env });
        assert.strictEqual(target.querySelector(".custom").value, "");
        def.resolve();
        await nextTick();
        assert.strictEqual(target.querySelector(".custom").value, "foo");
        target.querySelector(".custom").value = "blob";
        await triggerEvent(target, ".custom", "input");
        def2.resolve();
        await nextTick();
        assert.strictEqual(target.querySelector(".custom").value, "blob");
    });
});
