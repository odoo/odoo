/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
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
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                        color: {
                            type: "selection",
                            selection: [
                                ["red", "Red"],
                                ["black", "Black"],
                            ],
                            default: "red",
                            string: "Color",
                        },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner_type", "Partner Type"],
                                ["partner", "Partner"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            reference: "product,37",
                        },
                        {
                            id: 2,
                            product_id: 37,
                        },
                    ],
                },
                product: {
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BadgeSelectionField");

    QUnit.test("BadgeSelectionField widget on a many2one in a new record", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="product_id" widget="selection_badge"/></form>',
        });

        assert.containsOnce(
            target,
            "div.o_field_selection_badge",
            "should have rendered outer div"
        );
        assert.containsN(target, "span.o_selection_badge", 2, "should have 2 possible choices");
        assert.strictEqual(
            target.querySelector("span.o_selection_badge").textContent,
            "xphone",
            "one of them should be xphone"
        );
        assert.containsNone(target, "span.active", "none of the input should be checked");

        await click(target.querySelector("span.o_selection_badge"));

        assert.containsOnce(target, "span.active", "one of the input should be checked");

        await click(target, ".o_form_button_save");

        var newRecord = serverData.models.partner.records.at(-1);
        assert.strictEqual(newRecord.product_id, 37, "should have saved record with correct value");
    });

    QUnit.test(
        "BadgeSelectionField widget on a selection in a new record",
        async function (assert) {
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: '<form><field name="color" widget="selection_badge"/></form>',
            });

            assert.containsOnce(
                target,
                "div.o_field_selection_badge",
                "should have rendered outer div"
            );
            assert.containsN(target, "span.o_selection_badge", 2, "should have 2 possible choices");
            assert.strictEqual(
                target.querySelector("span.o_selection_badge").textContent,
                "Red",
                "one of them should be Red"
            );

            // click on 2nd option
            await click(target.querySelector("span.o_selection_badge:last-child"));

            await click(target.querySelector(".o_form_button_save"));

            var newRecord = serverData.models.partner.records.at(-1);
            assert.strictEqual(
                newRecord.color,
                "black",
                "should have saved record with correct value"
            );
        }
    );

    QUnit.test(
        "BadgeSelectionField widget on a selection in a readonly mode",
        async function (assert) {
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: '<form><field name="color" widget="selection_badge" readonly="1"/></form>',
            });

            assert.containsOnce(
                target,
                "div.o_readonly_modifier span",
                "should have 1 possible value in readonly mode"
            );
        }
    );

    QUnit.test(
        "BadgeSelectionField widget on a selection unchecking selected value",
        async (assert) => {
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: '<form><field name="color" widget="selection_badge"/></form>',
                mockRPC(_, { method, model, args }) {
                    if (method === "web_save" && model === "partner") {
                        assert.step("web_save");
                        assert.deepEqual(args[1], { color: false });
                    }
                },
            });

            assert.containsOnce(
                target,
                "div.o_field_selection_badge",
                "should have rendered outer div"
            );
            assert.containsN(target, "span.o_selection_badge", 2, "should have 2 possible choices");
            assert.containsN(target, "span.o_selection_badge.active", 1, "one is active");
            assert.strictEqual(
                target.querySelector("span.o_selection_badge.active").textContent,
                "Red",
                "the active one should be Red"
            );

            // click again on red option and save to update the server data
            await click(target, "span.o_selection_badge.active");
            assert.verifySteps([]);
            await click(target, ".o_form_button_save");
            assert.verifySteps(["web_save"], "should have created a new record");

            const newRecord = serverData.models.partner.records.at(-1);
            assert.strictEqual(
                newRecord.color,
                false,
                "the new value should be false as we have selected same value as default"
            );
        }
    );

    QUnit.test(
        "BadgeSelectionField widget on a selection unchecking selected value (required field)",
        async (assert) => {
            serverData.models.partner.fields.color.required = true;
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: '<form><field name="color" widget="selection_badge"/></form>',
                mockRPC(_, { method, model, args }) {
                    if (method === "web_save" && model === "partner") {
                        assert.step("web_save");
                        assert.deepEqual(args[1], { color: "red" });
                    }
                },
            });

            assert.containsOnce(
                target,
                "div.o_field_selection_badge",
                "should have rendered outer div"
            );
            assert.containsN(target, "span.o_selection_badge", 2, "should have 2 possible choices");
            assert.containsN(target, "span.o_selection_badge.active", 1, "one is active");
            assert.strictEqual(
                target.querySelector("span.o_selection_badge.active").textContent,
                "Red",
                "the active one should be Red"
            );

            // click again on red option and save to update the server data
            await click(target, "span.o_selection_badge.active");
            assert.verifySteps([]);
            await click(target, ".o_form_button_save");
            assert.verifySteps(["web_save"], "should have created a new record");

            const newRecord = serverData.models.partner.records.at(-1);
            assert.strictEqual(
                newRecord.color,
                "red",
                "the new value should be red"
            );
        }
    );
});
