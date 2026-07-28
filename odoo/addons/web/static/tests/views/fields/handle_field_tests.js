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
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            p: [],
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            p: [],
                            sequence: 4,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            sequence: 9,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("HandleField");

    QUnit.test("HandleField in x2m", async function (assert) {
        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="sequence" widget="handle" />
                            <field name="display_name" />
                        </tree>
                    </field>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector("td span.o_row_handle").textContent,
            "",
            "handle should not have any content"
        );

        assert.isVisible(
            target.querySelector("td span.o_row_handle"),
            "handle should be invisible"
        );

        assert.containsN(target, "span.o_row_handle", 2, "should have 2 handles");

        assert.hasClass(
            target.querySelector("td"),
            "o_handle_cell",
            "column widget should be displayed in css class"
        );

        assert.notStrictEqual(
            getComputedStyle(target.querySelector("td span.o_row_handle")).display,
            "none",
            "handle should be visible in edit mode"
        );

        await click(target.querySelectorAll("td")[1]);
        assert.containsOnce(
            target.querySelector("td"),
            "span.o_row_handle",
            "content of the cell should have been replaced"
        );
    });

    QUnit.test("HandleField with falsy values", async function (assert) {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
                    <field name="sequence" widget="handle" />
                    <field name="display_name" />
                </tree>`,
        });

        const visibleRowHandles = [...target.querySelectorAll(".o_row_handle")].filter(
            (el) => getComputedStyle(el).display !== "none"
        );

        assert.containsN(
            target,
            visibleRowHandles,
            serverData.models.partner.records.length,
            "there should be a visible handle for each record"
        );
    });

    QUnit.test("HandleField in a readonly one2many", async function (assert) {
        serverData.models.partner.records[0].p = [1, 2, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" readonly="1">
                        <tree editable="top">
                            <field name="sequence" widget="handle" />
                            <field name="display_name" />
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsN(target, ".o_row_handle", 3, "there should be 3 handles, one for each row");
        assert.strictEqual(
            getComputedStyle(target.querySelector("td span.o_row_handle")).display,
            "none",
            "handle should be invisible"
        );
    });
});
