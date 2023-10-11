/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { attachComponent, useWidget } from "@web/legacy/utils";

    import { makeTestEnv } from "@web/../tests/helpers/mock_env";
    import { getFixture, mount } from "@web/../tests/helpers/utils";
    import Widget from "@web/legacy/js/core/widget";
    import {
        Component,
        onMounted,
        onPatched,
        onWillDestroy,
        onWillStart,
        onWillUpdateProps,
        useRef,
        useState,
        xml,
    } from "@odoo/owl";
    import { nextTick } from "./helpers/test_utils";

    QUnit.module("Owl Compatibility", function () {
        QUnit.test("useWidget", async (assert) => {
            assert.expect(9);

            let widget = null;
            const CustomWidget = Widget.extend({
                init(_, ...params) {
                    this._super(...arguments);
                    widget = this;
                    assert.step("widget initialized");
                    assert.deepEqual(params, ["a", 1]);
                    this.params = params;
                },
                start() {
                    this.$el.text("Hello World!");
                },
                callTriggerUp() {
                    this.call("test", "call", { [this.params[0]]: this.params[1] });
                },
            });

            class ComponentAdapter extends Component {
                static template = xml`<div id="adapter" t-ref="container"/>`;
                setup() {
                    this.containerRef = useRef("container");
                    this.widget = useWidget("container", CustomWidget, ["a", 1]);
                    assert.strictEqual(this.widget, widget);
                }
            }

            class Toggle extends Component {
                static components = { ComponentAdapter };
                static template = xml`<ComponentAdapter t-if="state.active"/>`;
                state = useState({ active: true });
            }

            const target = getFixture();
            registry.category("services").add("test", {
                start: () => ({
                    call: (p) => {
                        assert.step("triggered up");
                        assert.deepEqual(p, { a: 1 });
                    },
                }), 
            });
            const component = await mount(Toggle, target, {
                env: await makeTestEnv(),
            });
            assert.verifySteps(["widget initialized"]);

            assert.strictEqual(
                target.querySelector("#adapter").textContent,
                "Hello World!"
            );

            widget.callTriggerUp();
            assert.verifySteps(["triggered up"]);

            component.state.active = false;
            await nextTick();
            assert.ok(widget.isDestroyed());
        });

        QUnit.test("attachComponent", async (assert) => {
            assert.expect(13);

            class CustomComponent extends Component {
                static template = xml`<div id="component" t-esc="props.text"/>`;
                setup() {
                    assert.step("setup");
                    onWillStart(() => assert.step("onWillStart"));
                    onMounted(() => assert.step("onMounted"));
                    onWillUpdateProps(() => assert.step("onWillUpdateProps"));
                    onPatched(() => assert.step("onPatched"));
                    onWillDestroy(() => assert.step("onWillDestroy"));
                }
            }

            const CustomWidget = Widget.extend({
                async start() {
                    this.el.id = "widget";
                    this.component = await attachComponent(this, this.el, CustomComponent, { text: "Hello" });
                },
            });

            const target = getFixture();
            const widget = new CustomWidget();
            await widget.appendTo(target);

            assert.verifySteps(["setup", "onWillStart", "onMounted"]);
            assert.strictEqual(target.querySelector("#widget > #component").textContent, "Hello");

            widget.component.update({ text: "World" });
            await nextTick();
            assert.verifySteps(["onWillUpdateProps", "onPatched"]);
            assert.strictEqual(target.querySelector("#widget > #component").textContent, "World");

            widget.component.destroy();
            assert.verifySteps(["onWillDestroy"]);
            assert.containsOnce(target, "#widget");
            assert.containsNone(target, "#widget > #component");

            widget.destroy();
        });
    });
