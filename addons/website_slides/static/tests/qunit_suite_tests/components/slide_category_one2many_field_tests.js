/** @odoo-module */

import { click, clickEdit, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("SlideCategoryOneToManyField", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                partner: {
                    fields: { lines: { type: "one2many", relation: "lines_sections" } },
                    records: [
                        {
                            id: 1,
                            lines: [1, 2],
                        },
                    ],
                },
                lines_sections: {
                    fields: {
                        is_category: { type: "boolean" },
                        name: { type: "char", string: "Name" },
                        int: { type: "number", string: "Integer" },
                    },
                    records: [
                        {
                            id: 1,
                            is_category: true,
                            display_name: "firstSectionName",
                            name: "firstSectionTitle",
                            int: 4,
                        },
                        {
                            id: 2,
                            is_category: false,
                            display_name: "recordName",
                            name: "recordTitle",
                            int: 5,
                        },
                    ],
                },
            },
            views: {
                "lines_sections,false,form": `
                    <form>
                        <field name="display_name" />
                    </form>
                `,
            },
        };

        setupViewRegistries();
    });

    QUnit.test("basic rendering", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="lines" widget="slide_category_one2many">
                        <tree>
                            <field name="is_category" invisible="1" />
                            <field name="name" />
                            <field name="display_name" />
                            <field name="int" />
                        </tree>
                    </field>
                </form>
            `,
        });
        assert.containsOnce(target, ".o_field_x2many .o_list_renderer table.o_section_list_view");
        assert.containsN(target, ".o_data_row", 2);
        assert.hasClass(target.querySelectorAll(".o_data_row")[0], "o_is_section fw-bold");
        const rows = target.querySelectorAll(".o_data_row");
        assert.strictEqual(rows[0].textContent, "firstSectionTitle");
        assert.strictEqual(rows[1].textContent, "recordTitlerecordName5");
        assert.strictEqual(rows[0].querySelector("td[name=name]").getAttribute("colspan"), "3");
        assert.strictEqual(rows[1].querySelector("td[name=name]").getAttribute("colspan"), null);
    });

    QUnit.test("click on section behaves as usual in readonly mode", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="lines" widget="slide_category_one2many">
                        <tree>
                            <field name="is_category" invisible="1" />
                            <field name="name" />
                            <field name="int" />
                        </tree>
                    </field>
                </form>
            `,
        });
        await click(target.querySelector(".o_data_cell"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view_dialog");
    });

    QUnit.test("click on section edit the section in place", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="lines" widget="slide_category_one2many">
                        <tree>
                            <field name="is_category" invisible="1" />
                            <field name="name" />
                            <field name="int" />
                        </tree>
                    </field>
                </form>`,
        });
        await clickEdit(target);
        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(target.querySelector(".o_is_section"), "o_selected_row");
        assert.containsNone(target, ".modal .o_form_view_dialog");
    });

    QUnit.test("click on real line opens a dialog", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="lines" widget="slide_category_one2many">
                        <tree>
                            <field name="is_category" invisible="1" />
                            <field name="name" />
                            <field name="int" />
                        </tree>
                    </field>
                </form>
            `,
        });
        await clickEdit(target);
        await click(target.querySelector(".o_data_row:nth-child(2) .o_data_cell"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view_dialog");
    });

    QUnit.test("can create section inline", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="lines" widget="slide_category_one2many">
                        <tree>
                            <field name="is_category" invisible="1" />
                            <field name="name" />
                            <field name="int" />
                            <control>
                                <create string="add line" />
                                <create string="add section" context="{'default_is_category': true}" />
                            </control>
                        </tree>
                    </field>
                </form>
            `,
        });

        await clickEdit(target);
        assert.containsNone(target, ".o_selected_row.o_is_section");

        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[1]);
        assert.containsOnce(target, ".o_selected_row.o_is_section");
        assert.containsNone(target, ".modal .o_form_view_dialog");
    });

    QUnit.test("creates real record in form dialog", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="lines" widget="slide_category_one2many">
                        <tree>
                            <field name="is_category" invisible="1" />
                            <field name="name" />
                            <field name="int" />
                            <control>
                                <create string="add line" />
                                <create string="add section" context="{'default_is_category': true}" />
                            </control>
                        </tree>
                    </field>
                </form>
            `,
        });

        await clickEdit(target);
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view_dialog");
    });
});
