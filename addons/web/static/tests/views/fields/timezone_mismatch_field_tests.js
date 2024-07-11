/** @odoo-module **/

import { click, editSelect, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        color: {
                            type: "selection",
                            selection: [
                                ["red", "Red"],
                                ["black", "Black"],
                            ],
                            default: "red",
                        },
                        tz_offset: {
                            string: "tz_offset",
                            type: "char",
                        },
                    },
                    records: [
                        { id: 1, color: "red", tz_offset: 0 },
                        { id: 2, color: "red", tz_offset: 0 },
                        { id: 3, color: "red", tz_offset: 0 },
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.module("TimezoneMismatchField");

    QUnit.test("widget timezone_mismatch in a list view", async function (assert) {
        assert.expect(5);

        serverData.models.partner.onchanges = {
            color: function (r) {
                r.tz_offset = "+4800"; // make sure we have a mismatch
            },
        };

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: /*xml*/ `
                <tree string="Colors" editable="top">
                    <field name="tz_offset" column_invisible="True"/>
                    <field name="color" widget="timezone_mismatch" />
                </tree>
            `,
        });

        assert.containsN(target, "td:contains(Red)", 3, "should have 3 rows with correct value");

        await click(
            target
                .querySelectorAll(".o_data_row")[0]
                .querySelector("td:not(.o_list_record_selector)")
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name=color] select",
            "td should have a child 'select'"
        );

        const td = target.querySelector("tbody tr.o_selected_row td:not(.o_list_record_selector)");
        assert.strictEqual(
            td.querySelector(".o_field_widget[name=color] select").parentElement.childElementCount,
            1,
            "select tag should be only child of td"
        );

        await editSelect(td, "select", '"black"');
        assert.containsOnce(td, ".o_tz_warning", "Should display icon alert");
        assert.ok(
            td
                .querySelector("select option:checked")
                .textContent.match(/Black\s+\([0-9]+\/[0-9]+\/[0-9]+ [0-9]+:[0-9]+:[0-9]+\)/),
            "Should display the datetime in the selected timezone"
        );
    });

    QUnit.test("widget timezone_mismatch in a form view", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.tz = {
            type: "selection",
            selection: [
                ["Europe/Brussels", "Europe/Brussels"],
                ["America/Los_Angeles", "America/Los_Angeles"],
            ],
        };
        serverData.models.partner.records[0].tz = false;
        serverData.models.partner.records[0].tz_offset = "+4800";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: /*xml*/ `
                <form>
                    <field name="tz_offset" invisible="True"/>
                    <field name="tz" widget="timezone_mismatch" />
                </form>
            `,
        });

        assert.containsOnce(target, 'div[name="tz"] select');
        assert.containsOnce(target, ".o_tz_warning", "warning class should be there.");
    });

    QUnit.test(
        "widget timezone_mismatch in a form view edit mode with mismatch",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.fields.tz = {
                type: "selection",
                selection: [
                    ["Europe/Brussels", "Europe/Brussels"],
                    ["America/Los_Angeles", "America/Los_Angeles"],
                ],
            };
            serverData.models.partner.records[0].tz = "America/Los_Angeles";
            serverData.models.partner.records[0].tz_offset = "+4800";

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: /*xml*/ `
                    <form>
                        <field name="tz_offset" invisible="True"/>
                        <field name="tz" widget="timezone_mismatch" options="{'tz_offset_field': 'tz_offset'}"/>
                    </form>
                `,
            });

            assert.containsN(
                target,
                'div[name="tz"] select option',
                3,
                "The select element should have 3 children"
            );
            assert.containsOnce(target, ".o_tz_warning", "timezone mismatch is present");
            assert.notOk(
                target.querySelector(".o_tz_warning").children.length,
                "The mismatch element should not have children"
            );
        }
    );
});
