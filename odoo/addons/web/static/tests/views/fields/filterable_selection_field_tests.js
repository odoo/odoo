/** @odoo-module **/

import { editSelect, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

// Note: the containsN always check for one more as there will be an invisible empty option every time.
QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                program: {
                    fields: {
                        program_type: {
                            type: "selection",
                            selection: [
                                ["coupon", "Coupons"],
                                ["promotion", "Promotion"],
                                ["gift_card", "gift_card"],
                            ],
                            required: true,
                        }
                    },
                    records: [
                        { id: 1, program_type: "coupon" },
                        { id: 2, program_type: "gift_card" },
                    ],
                },
            }
        }
        setupViewRegistries();
    });

    QUnit.module("utils");

    QUnit.test("FilterableSelectionField test whitelist", async (assert) => {
        await makeView({
            type: "form",
            resModel: "program",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="program_type" widget="filterable_selection" options="{'whitelisted_values': ['coupons', 'promotion']}"/>
                </form>`,
        });

        assert.containsN(target, "select option", 3);
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"coupon\"']",
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"promotion\"']",
        );
    });

    QUnit.test("FilterableSelectionField test blacklist", async (assert) => {
        await makeView({
            type: "form",
            resModel: "program",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="program_type" widget="filterable_selection" options="{'blacklisted_values': ['gift_card']}"/>
                </form>`,
        });

        assert.containsN(target, "select option", 3);
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"coupon\"']",
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"promotion\"']",
        );
    });

    QUnit.test("FilterableSelectionField test with invalid value", async (assert) => {
        // The field should still display the current value in the list
        await makeView({
            type: "form",
            resModel: "program",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <field name="program_type" widget="filterable_selection" options="{'blacklisted_values': ['gift_card']}"/>
                </form>`,
        });

        assert.containsN(target, "select option", 4);
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"gift_card\"']",
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"coupon\"']",
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"promotion\"']",
        );

        await editSelect(target, ".o_field_widget[name='program_type'] select", '"coupon"');
        assert.containsN(target, "select option", 3);
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"coupon\"']",
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='program_type'] select option[value='\"promotion\"']",
        );
    });
});
