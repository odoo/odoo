import { attachComponent } from "@web_editor/js/core/owl_utils";

import { getFixture } from "@web/../tests/helpers/utils";
import publicWidget from "@web/legacy/js/public/public_widget";
import {
    Component,
    onMounted,
    onPatched,
    onWillDestroy,
    onWillStart,
    onWillUpdateProps,
    xml,
} from "@odoo/owl";
import { nextTick } from "@web/../tests/legacy/legacy_tests/helpers/test_utils";
import { makeTestEnv } from "@web/../tests/legacy/helpers/mock_env";

QUnit.module("Owl Compatibility", function () {
    QUnit.test("attachComponent", async (assert) => {
        assert.expect(13);

        class CustomComponent extends Component {
            static template = xml`<div id="component" t-esc="props.text"/>`;
            static props = ["*"];
            setup() {
                assert.step("setup");
                onWillStart(() => assert.step("onWillStart"));
                onMounted(() => assert.step("onMounted"));
                onWillUpdateProps(() => assert.step("onWillUpdateProps"));
                onPatched(() => assert.step("onPatched"));
                onWillDestroy(() => assert.step("onWillDestroy"));
            }
        }

        const CustomWidget = publicWidget.Widget.extend({
            async start() {
                this.el.id = "widget";
                this.component = await attachComponent(this, this.el, CustomComponent, { text: "Hello" });
            },
        });

        await makeTestEnv();

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
