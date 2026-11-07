/** @odoo-module **/

import { click, getFixture, triggerEvent, triggerHotkey } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Dynamic placeholder", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        char: {
                            string: "Char",
                            type: "char",
                        },
                        placeholder: {
                            string: "Placeholder",
                            type: "char",
                            default: "partner",
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            char: "yop",
                            product_id: 37,
                        },
                        {
                            id: 2,
                            char: "blip",
                            product_id: 41,
                        },
                    ],
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            name: "xphone",
                        },
                        {
                            id: 41,
                            name: "xpad",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.test("dynamic placeholder close on click out", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="placeholder" invisible="1"/>
                    <sheet>
                        <group>
                            <field
                                name="char"
                                options="{
                                    'dynamic_placeholder': true,
                                    'dynamic_placeholder_model_reference_field': 'placeholder'
                                }"
                            />
                        </group>
                    </sheet>
                </form>
            `,
        });

        await triggerEvent(target, ".o_field_char input", "keydown", { key: "#" });
        assert.containsOnce(target, ".o_model_field_selector_popover");
        await click(target, ".o_content");
        assert.containsNone(target, ".o_model_field_selector_popover");
        await triggerEvent(target, ".o_field_char input", "keydown", { key: "#" });
        await click(target, ".o_model_field_selector_popover_item_relation");
        await click(target, ".o_content");
        assert.containsNone(target, ".o_model_field_selector_popover");
    });

    QUnit.test("dynamic placeholder close with escape", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="placeholder" invisible="1"/>
                    <sheet>
                        <group>
                            <field
                                name="char"
                                options="{
                                    'dynamic_placeholder': true,
                                    'dynamic_placeholder_model_reference_field': 'placeholder'
                                }"
                            />
                        </group>
                    </sheet>
                </form>
            `,
        });

        await triggerEvent(target, ".o_field_char input", "keydown", { key: "#" });
        assert.containsOnce(target, ".o_model_field_selector_popover");
        await triggerHotkey("Escape");
        assert.containsNone(target, ".o_model_field_selector_popover");
        await triggerEvent(target, ".o_field_char input", "keydown", { key: "#" });
        await click(target, ".o_model_field_selector_popover_item_relation");
        await triggerHotkey("Escape");
        assert.containsNone(target, ".o_model_field_selector_popover");
    });

    QUnit.test("dynamic placeholder close when clicking on the cross", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="placeholder" invisible="1"/>
                    <sheet>
                        <group>
                            <field
                                name="char"
                                options="{
                                    'dynamic_placeholder': true,
                                    'dynamic_placeholder_model_reference_field': 'placeholder'
                                }"
                            />
                        </group>
                    </sheet>
                </form>
            `,
        });

        await triggerEvent(target, ".o_field_char input", "keydown", { key: "#" });
        assert.containsOnce(target, ".o_model_field_selector_popover");
        await click(target, ".o_model_field_selector_popover_close");
        assert.containsNone(target, ".o_model_field_selector_popover");
        await triggerEvent(target, ".o_field_char input", "keydown", { key: "#" });
        await click(target, ".o_model_field_selector_popover_item_relation");
        await click(target, ".o_model_field_selector_popover_close");
        assert.containsNone(target, ".o_model_field_selector_popover");
    });
});
