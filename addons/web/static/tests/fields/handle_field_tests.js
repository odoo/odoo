/** @odoo-module **/

import { click, getFixture } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

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

    QUnit.skipWOWL("HandleField in x2m", async function (assert) {
        assert.expect(6);

        serverData.models.partner.records[0].p = [2, 4];
        const form = await makeView({
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
                </form>
            `,
        });

        assert.strictEqual(
            target.querySelector("td span.o_row_handle").textContent,
            "",
            "handle should not have any content"
        );

        assert.strictEqual(
            getComputedStyle(target.querySelector("td span.o_row_handle")).display,
            "none",
            "handle should be invisible in readonly mode"
        );

        assert.containsN(target, "span.o_row_handle", 2, "should have 2 handles");

        await click(target, ".o_form_button_edit");

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
        assert.expect(1);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
                    <field name="sequence" widget="handle" />
                    <field name="display_name" />
                </tree>
            `,
        });

        const visibleRowHandles = [...target.querySelectorAll(".o_row_handle")].filter(
            (el) => getComputedStyle(el).display !== "none"
        );

        assert.containsN(
            list,
            visibleRowHandles,
            serverData.models.partner.records.length,
            "there should be a visible handle for each record"
        );
    });
});
