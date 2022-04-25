/** @odoo-module **/

import { click, getFixture, triggerEvent } from "@web/../tests/helpers/utils";
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
                        display_name: { string: "Displayed name", type: "char" },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "trululu",
                        },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            int_field: 10,
                            p: [1],
                        },
                    ],
                    onchanges: {},
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char" },
                        color: { string: "Color index", type: "integer" },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.module("Many2ManyCheckBoxesField");

    QUnit.test("Many2ManyCheckBoxesField", async function (assert) {
        serverData.models.partner.records[0].timmy = [12];
        const commands = [[[6, false, [12, 14]]], [[6, false, [14]]]];
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="timmy" widget="many2many_checkboxes" />
                    </group>
                </form>
            `,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.step("write");
                    assert.deepEqual(args.args[1].timmy, commands.shift());
                }
            },
        });

        assert.containsN(target, "div.o_field_widget div.custom-checkbox", 2);

        let checkboxes = target.querySelectorAll("div.o_field_widget div.custom-checkbox input");
        assert.ok(checkboxes[0].checked);
        assert.notOk(checkboxes[1].checked);

        assert.containsN(target, "div.o_field_widget div.custom-checkbox input:disabled", 2);

        await click(target, ".o_form_button_edit");

        assert.containsNone(target, "div.o_field_widget div.custom-checkbox input:disabled");

        // add a m2m value by clicking on input
        checkboxes = target.querySelectorAll("div.o_field_widget div.custom-checkbox input");
        await click(checkboxes[1]);
        await click(target, ".o_form_button_save");
        assert.containsN(target, "div.o_field_widget div.custom-checkbox input:checked", 2);

        // remove a m2m value by clinking on label
        await click(target, ".o_form_button_edit");
        await click(target.querySelector("div.o_field_widget div.custom-checkbox > label"));
        await click(target, ".o_form_button_save");
        checkboxes = target.querySelectorAll("div.o_field_widget div.custom-checkbox input");
        assert.notOk(checkboxes[0].checked);
        assert.ok(checkboxes[1].checked);

        assert.verifySteps(["write", "write"]);
    });

    QUnit.test("Many2ManyCheckBoxesField (readonly)", async function (assert) {
        assert.expect(7);

        serverData.models.partner.records[0].timmy = [12];
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="timmy" widget="many2many_checkboxes" attrs="{'readonly': true}" />
                    </group>
                </form>
            `,
        });

        assert.containsN(
            target,
            "div.o_field_widget div.custom-checkbox",
            2,
            "should have fetched and displayed the 2 values of the many2many"
        );

        assert.ok(
            target.querySelector("div.o_field_widget div.custom-checkbox input").checked,
            "first checkbox should be checked"
        );
        assert.notOk(
            target.querySelectorAll("div.o_field_widget div.custom-checkbox input")[1].checked,
            "second checkbox should not be checked"
        );

        assert.containsN(
            target,
            "div.o_field_widget div.custom-checkbox input:disabled",
            2,
            "the checkboxes should be disabled"
        );

        await click(target, ".o_form_button_edit");

        assert.containsN(
            target,
            "div.o_field_widget div.custom-checkbox input:disabled",
            2,
            "the checkboxes should be disabled"
        );

        await click(target.querySelectorAll("div.o_field_widget div.custom-checkbox > label")[1]);

        assert.ok(
            target.querySelector("div.o_field_widget div.custom-checkbox input").checked,
            "first checkbox should be checked"
        );
        assert.notOk(
            target.querySelectorAll("div.o_field_widget div.custom-checkbox input")[1].checked,
            "second checkbox should not be checked"
        );
    });

    QUnit.test(
        "Many2ManyCheckBoxesField: start non empty, then remove twice",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].timmy = [12, 14];
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="timmy" widget="many2many_checkboxes" />
                        </group>
                    </form>
                `,
            });

            await click(target, ".o_form_button_edit");

            await click(target.querySelectorAll("div.o_field_widget div.custom-checkbox input")[0]);
            await click(target.querySelectorAll("div.o_field_widget div.custom-checkbox input")[1]);
            await click(target, ".o_form_button_save");
            assert.notOk(
                target.querySelectorAll("div.o_field_widget div.custom-checkbox input")[0].checked,
                "first checkbox should not be checked"
            );
            assert.notOk(
                target.querySelectorAll("div.o_field_widget div.custom-checkbox input")[1].checked,
                "second checkbox should not be checked"
            );
        }
    );

    QUnit.test(
        "Many2ManyCheckBoxesField: values are updated when domain changes",
        async function (assert) {
            assert.expect(5);

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="int_field" />
                        <field name="timmy" widget="many2many_checkboxes" domain="[['id', '>', int_field]]" />
                    </form>
                `,
            });

            await click(target, ".o_form_button_edit");

            assert.strictEqual(
                target.querySelector(".o_field_widget[name='int_field'] input").value,
                "10"
            );
            assert.containsN(target, ".o_field_widget[name='timmy'] .custom-checkbox", 2);
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='timmy']").textContent,
                "goldsilver"
            );

            const input = target.querySelector(".o_field_widget[name='int_field'] input");
            input.value = 13;
            await triggerEvent(input, null, "change");

            assert.containsOnce(target, ".o_field_widget[name='timmy'] .custom-checkbox");
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='timmy']").textContent,
                "silver"
            );
        }
    );

    QUnit.test("Many2ManyCheckBoxesField with 40+ values", async function (assert) {
        // 40 is the default limit for x2many fields. However, the many2many_checkboxes is a
        // special field that fetches its data through the fetchSpecialData mechanism, and it
        // uses the name_search server-side limit of 100. This test comes with a fix for a bug
        // that occurred when the user (un)selected a checkbox that wasn't in the 40 first checkboxes,
        // because the piece of data corresponding to that checkbox hadn't been processed by the
        // BasicModel, whereas the code handling the change assumed it had.
        assert.expect(3);

        const records = [];
        for (let id = 1; id <= 90; id++) {
            records.push({
                id,
                display_name: `type ${id}`,
                color: id % 7,
            });
        }
        serverData.models.partner_type.records = records;
        serverData.models.partner.records[0].timmy = records.map((r) => r.id);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_checkboxes" />
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "write") {
                    const expectedIds = records.map((r) => r.id);
                    expectedIds.pop();
                    assert.deepEqual(args[1].timmy, [[6, false, expectedIds]]);
                }
            },
        });

        await click(target, ".o_form_button_edit");

        assert.containsN(
            target,
            ".o_field_widget[name='timmy'] input[type='checkbox']:checked",
            90
        );

        // toggle the last value
        let checkboxes = target.querySelectorAll(
            ".o_field_widget[name='timmy'] input[type='checkbox']"
        );
        await click(checkboxes[checkboxes.length - 1]);

        await click(target, ".o_form_button_save");
        checkboxes = target.querySelectorAll(
            ".o_field_widget[name='timmy'] input[type='checkbox']"
        );
        assert.notOk(checkboxes[checkboxes.length - 1].checked);
    });

    QUnit.test("Many2ManyCheckBoxesField with 100+ values", async function (assert) {
        // The many2many_checkboxes widget limits the displayed values to 100 (this is the
        // server-side name_search limit). This test encodes a scenario where there are more than
        // 100 records in the co-model, and all values in the many2many relationship aren't
        // displayed in the widget (due to the limit). If the user (un)selects a checkbox, we don't
        // want to remove all values that aren't displayed from the relation.
        assert.expect(8);

        const records = [];
        for (let id = 1; id < 150; id++) {
            records.push({
                id,
                display_name: `type ${id}`,
                color: id % 7,
            });
        }
        serverData.models.partner_type.records = records;
        serverData.models.partner.records[0].timmy = records.map((r) => r.id);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_checkboxes" />
                </form>
            `,
            async mockRPC(route, { args, method }, performRPC) {
                if (method === "write") {
                    const expectedIds = records.map((r) => r.id);
                    expectedIds.shift();
                    assert.deepEqual(args[1].timmy, [[6, false, expectedIds]]);
                    assert.step("write");
                }
                const result = await performRPC(...arguments);
                if (method === "name_search") {
                    assert.strictEqual(
                        result.length,
                        100,
                        "sanity check: name_search automatically sets the limit to 100"
                    );
                    assert.step("name_search");
                }
                return result;
            },
        });

        await click(target, ".o_form_button_edit");

        assert.containsN(
            target,
            ".o_field_widget[name='timmy'] input[type='checkbox']",
            100,
            "should only display 100 checkboxes"
        );
        assert.ok(
            target.querySelector(".o_field_widget[name='timmy'] input[type='checkbox']").checked
        );

        // toggle the first value
        await click(target.querySelector(".o_field_widget[name='timmy'] input[type='checkbox']"));

        await click(target, ".o_form_button_save");
        assert.notOk(
            target.querySelector(".o_field_widget[name='timmy'] input[type='checkbox']").checked
        );
        assert.verifySteps(["name_search", "write"]);
    });

    QUnit.test("Many2ManyCheckBoxesField in a one2many", async function (assert) {
        assert.expect(3);

        serverData.models.partner_type.records.push({ id: 15, display_name: "bronze" });
        serverData.models.partner.records[0].timmy = [14, 15];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree><field name="id"/></tree>
                        <form>
                            <field name="timmy" widget="many2many_checkboxes"/>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], {
                        p: [[1, 1, { timmy: [[6, false, [15, 12]]] }]],
                    });
                }
            },
            resId: 1,
        });

        await click(target, ".o_form_button_edit");
        await click(target.querySelector(".o_data_cell"));

        // edit the timmy field by (un)checking boxes on the widget
        const firstCheckbox = target.querySelector(".modal .custom-control-input");
        await click(firstCheckbox);
        assert.ok(firstCheckbox.checked, "the checkbox should be ticked");
        const secondCheckbox = target.querySelectorAll(".modal .custom-control-input")[1];
        await click(secondCheckbox);
        assert.notOk(secondCheckbox.checked, "the checkbox should be unticked");

        await click(target.querySelector(".modal .o_form_button_save"));
        await click(target.querySelector(".o_form_button_save"));
    });
});
