/** @odoo-module */

import { click } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;

QUnit.module("SlideCategoryOneToManyField", {
    beforeEach() {
        serverData = {
            models: {
                partner: {
                    fields: { lines: { type: "one2many", relation: "lines_sections" } },
                    records: [{ id: 1, lines: [1, 2] }],
                },
                lines_sections: {
                    fields: {
                        is_category: { type: "boolean" },
                        name: { type: "char", string: "Name" },
                        int: { type: "integer", string: "Integer" },
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
                        <field name="display_name"/>
                    </form>`,
            },
        };

        setupViewRegistries();
    },
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
                        <field name="is_category" column_invisible="1"/>
                        <field name="name"/>
                        <field name="display_name"/>
                        <field name="int"/>
                    </tree>
                </field>
            </form>`,
    });
    assert.containsOnce($, ".o_field_x2many .o_list_renderer table.o_section_list_view");
    assert.containsN($, ".o_data_row", 2);
    assert.hasClass($(".o_data_row:eq(0)"), "o_is_section fw-bold");
    assert.strictEqual($(".o_data_row:eq(0)").text(), "firstSectionTitle");
    assert.strictEqual($(".o_data_row:eq(1)").text(), "recordTitlerecordName5");
    assert.strictEqual($(".o_data_row:eq(0) td[name=name]")[0].getAttribute("colspan"), "3");
    assert.strictEqual($(".o_data_row:eq(1) td[name=name]")[0].getAttribute("colspan"), null);
});

QUnit.test("click on section behaves as usual in readonly mode", async (assert) => {
    await makeView({
        type: "form",
        resModel: "partner",
        resId: 1,
        serverData,
        mode: "readonly",
        arch: `
            <form>
                <field name="lines" widget="slide_category_one2many">
                    <tree>
                        <field name="is_category" column_invisible="1"/>
                        <field name="name"/>
                        <field name="int"/>
                    </tree>
                </field>
            </form>`,
    });
    await click($(".o_data_cell")[0]);
    assert.containsNone($, ".o_selected_row");
    assert.containsOnce($, ".modal .o_form_view");
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
                        <field name="is_category" column_invisible="1"/>
                        <field name="name"/>
                        <field name="int"/>
                    </tree>
                </field>
            </form>`,
    });
    await click($(".o_data_cell")[0]);
    assert.hasClass($(".o_is_section"), "o_selected_row");
    assert.containsNone($, ".modal .o_form_view");
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
                        <field name="is_category" column_invisible="1"/>
                        <field name="name"/>
                        <field name="int"/>
                    </tree>
                </field>
            </form>`,
    });
    await click($(".o_data_row:nth-child(2) .o_data_cell")[0]);
    assert.containsOnce($, ".modal .o_form_view");
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
                        <field name="is_category" column_invisible="1"/>
                        <field name="name"/>
                        <field name="int"/>
                        <control>
                            <create string="add line"/>
                            <create string="add section" context="{'default_is_category': true}"/>
                        </control>
                    </tree>
                </field>
            </form>`,
    });
    assert.containsNone($, ".o_selected_row.o_is_section");

    await click($(".o_field_x2many_list_row_add a")[1]);
    assert.containsOnce($, ".o_selected_row.o_is_section");
    assert.containsNone($, ".modal .o_form_view");
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
                        <field name="is_category" column_invisible="1"/>
                        <field name="name"/>
                        <field name="int"/>
                        <control>
                            <create string="add line"/>
                            <create string="add section" context="{'default_is_category': true}"/>
                        </control>
                    </tree>
                </field>
            </form>`,
    });

    await click($(".o_field_x2many_list_row_add a")[0]);
    assert.containsNone($, ".o_selected_row");
    assert.containsOnce($, ".modal .o_form_view");
});
