/** @odoo-module **/

import {
    getModelFieldSelectorValues,
    openModelFieldSelectorPopover,
} from "@web/../tests/core/model_field_selector_tests";
import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        model: { string: "Model", type: "char" },
                        update_path: { string: "Path", type: "char" },
                        foo: { string: "Foo", type: "char" },
                    },
                    records: [{ id: 1, model: "partner", update_path: "foo" }],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.module("DynamicModelFieldSelectorChar");

    QUnit.test("invalid path typed in debug input is discarded", async function (assert) {
        patchWithCleanup(odoo, { debug: true });
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="model"/>
                    <field name="update_path" widget="DynamicModelFieldSelectorChar" options="{'model': 'model'}"/>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange");
                }
            },
        });
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);

        await openModelFieldSelectorPopover(target);
        await editInput(target, ".o_model_field_selector_debug", "not_a_field");
        assert.deepEqual(getModelFieldSelectorValues(target), ["not_a_field"]);

        await click(target, ".o_model_field_selector_popover_close");
        assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);
        assert.containsNone(target, ".o_model_field_selector_warning");
        assert.hasClass(target.querySelector(".o_form_status_indicator_buttons"), "invisible");
        assert.verifySteps([]);
    });

    QUnit.test(
        "invalid path typed in debug input is discarded on click away",
        async function (assert) {
            patchWithCleanup(odoo, { debug: true });
            await makeView({
                type: "form",
                serverData,
                resModel: "partner",
                resId: 1,
                arch: `
                <form>
                    <field name="model"/>
                    <field name="update_path" widget="DynamicModelFieldSelectorChar" options="{'model': 'model'}"/>
                </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.step("onchange");
                    }
                },
            });
            assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);

            await openModelFieldSelectorPopover(target);
            const input = target.querySelector(".o_model_field_selector_debug");
            input.value = "not_a_field";
            await triggerEvent(input, null, "input");

            // clicking away closes the popover (pointerdown), then blurs the input (change),
            // in the same task
            triggerEvent(target, ".o_form_view", "pointerdown");
            await triggerEvent(input, null, "change");
            await nextTick();
            assert.containsNone(target, ".o_model_field_selector_popover");
            assert.deepEqual(getModelFieldSelectorValues(target), ["Foo"]);
            assert.containsNone(target, ".o_model_field_selector_warning");
            assert.hasClass(target.querySelector(".o_form_status_indicator_buttons"), "invisible");
            assert.verifySteps([]);
        }
    );
});
