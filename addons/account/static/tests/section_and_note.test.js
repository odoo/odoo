import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame, edit, press, queryAllTexts } from "@odoo/hoot-dom";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class InvoiceLine extends models.Model {
    _name = "invoice_line";
    _records = [
        { id: 1, name: "r1", display_type: false, sequence: 1, m2m: [1] },
        { id: 2, name: "r2", display_type: false, sequence: 2, m2m: [2] },
        { id: 3, name: "A", display_type: "line_section", sequence: 3, m2m: [1] },
        { id: 4, name: "A1", display_type: false, sequence: 4, m2m: [1, 3] },
        { id: 5, name: "A2", display_type: false, sequence: 5, m2m: [1, 2] },
        { id: 6, name: "B", display_type: "line_section", sequence: 6, m2m: [2] },
        { id: 7, name: "B1", display_type: false, sequence: 7, m2m: [1, 3] },
        { id: 8, name: "B2", display_type: false, sequence: 8, m2m: [] },
        { id: 9, name: "Ba", display_type: "line_subsection", sequence: 9, m2m: [3] },
        { id: 10, name: "Ba1", display_type: false, sequence: 10, m2m: [2, 3] },
        { id: 11, name: "Ba2", display_type: false, sequence: 11, m2m: [3] },
        { id: 12, name: "C", display_type: "line_section", sequence: 12, m2m: [1] },
        { id: 13, name: "C1", display_type: false, sequence: 13, m2m: [] },
    ];

    name = fields.Char();
    display_type = fields.Selection({
        default: false,
        selection: [
            ["line_section", "Section"],
            ["line_subsection", "Subsection"],
            ["line_note", "Note"],
        ],
    });
    invoice_id = fields.Many2one({
        string: "Invoice",
        relation: "invoice",
    });
    sequence = fields.Integer();
    m2m = fields.Many2many({ relation: "bar" });
}
class Invoice extends models.Model {
    _records = [
        {
            id: 1,
            invoice_line_ids: Array.from({ length: InvoiceLine._records.length }, (_, i) => i + 1),
        },
    ];

    invoice_line_ids = fields.One2many({ relation: "invoice_line" });
}

class Bar extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Value 1" },
        { id: 2, name: "Value 2" },
        { id: 3, name: "Value 3" },
    ];
}

defineModels([Invoice, InvoiceLine, Bar]);
defineMailModels();

onRpc("has_group", () => true);

test("can add a line in a section", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(0) button").click();
    await contains(".o-dropdown-item:contains(Add a line)").click();
    await edit("A3");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "A3",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
});

test("can add a line in a subsection", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:last button").click();
    await contains(".o-dropdown-item:contains(Add a line)").click();
    await edit("Ca3");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
        "Ca3",
    ]);
});

test("can add a subsection in a section", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(0) button").click();
    await contains(".o-dropdown-item:contains(Add a subsection)").click();
    await edit("Aa");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "Aa",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    expect(".o_is_line_subsection:contains(Aa)").toHaveCount(1);
});

test("can't add a subsection if value not in selection", async () => {
    InvoiceLine._records[10].display_type = "line_section";
    InvoiceLine._fields.display_type = fields.Selection({
        default: false,
        selection: [
            ["line_section", "Section"],
            ["line_note", "Note"],
        ],
    });

    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    await contains(".o_list_section_options:last button").click();
    expect(".o-dropdown-item:contains(Add a subsection)").toHaveCount(0);
});

test("can add a section after another", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(0) button").click();
    await contains(".o-dropdown-item:contains(Add a section)").click();
    await edit("D");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "D",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    expect(`.o_is_line_section:contains(D)`).toHaveCount(1);
});

test("can add a subsection after another", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_is_line_subsection .o_list_section_options button").click();
    await contains(".o-dropdown-item:contains(Add a subsection)").click();
    await edit("Bb");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "Bb",
        "C",
        "C1",
    ]);
    expect(`.o_is_line_subsection:contains(Bb)`).toHaveCount(1);
});

test("can delete sections", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(1) button").click();
    await contains(".o-dropdown-item:contains(Delete)").click();
    expect(queryAllTexts(".o_data_row")).toEqual(["r1", "r2", "A", "A1", "A2", "C", "C1"]);
});

test("can delete subsections", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_is_line_subsection .o_list_section_options button").click();
    await contains(".o-dropdown-item:contains(Delete)").click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "C",
        "C1",
    ]);
});

test("can duplicate sections", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(1) button").click();
    await contains(".o-dropdown-item:contains(Duplicate)").click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
});

test("can duplicate subsections", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_is_line_subsection .o_list_section_options button").click();
    await contains(".o-dropdown-item:contains(Duplicate)").click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
});

test("can resequence records inside sections", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({
            invoice_line_ids: [
                [1, 4, { sequence: 1 }],
                [1, 1, { sequence: 2 }],
                [1, 2, { sequence: 3 }],
                [1, 3, { sequence: 4 }],
                [1, 6, { sequence: 6 }],
                [1, 7, { sequence: 7 }],
                [1, 8, { sequence: 8 }],
                [1, 9, { sequence: 9 }],
                [1, 10, { sequence: 10 }],
                [1, 11, { sequence: 11 }],
                [1, 5, { sequence: 12 }],
                [1, 13, { sequence: 5 }],
                [1, 12, { sequence: 13 }],
            ],
        });
    });
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });

    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_data_row:eq(3) .o_row_handle").dragAndDrop(".o_data_row:eq(0)");
    expect(queryAllTexts(".o_data_row")).toEqual([
        "A1",
        "r1",
        "r2",
        "A",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_data_row:eq(4) .o_row_handle").dragAndDrop(".o_data_row:eq(10)");
    expect(queryAllTexts(".o_data_row")).toEqual([
        "A1",
        "r1",
        "r2",
        "A",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "A2",
        "C",
        "C1",
    ]);
    await contains(".o_data_row:last .o_row_handle").dragAndDrop(".o_data_row:eq(4)");
    expect(queryAllTexts(".o_data_row")).toEqual([
        "A1",
        "r1",
        "r2",
        "A",
        "C1",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "A2",
        "C",
    ]);
    await clickSave();
    expect.verifySteps(["web_save"]);
});

test("resequence can be discarded", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });

    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_data_row:eq(3) .o_row_handle").dragAndDrop(".o_data_row:eq(0)");
    expect(queryAllTexts(".o_data_row")).toEqual([
        "A1",
        "r1",
        "r2",
        "A",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_form_button_cancel").click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
});

test("can resequence sections", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });

    await contains(".o_data_row:eq(11) .o_row_handle").dragAndDrop(".o_data_row:eq(0)");
    expect(queryAllTexts(".o_data_row")).toEqual(
        ["C", "r1", "r2", "A", "A1", "A2", "B", "B1", "B2", "Ba", "Ba1", "Ba2", "C1"],
        {
            message: "With C on top, B becomes the top section for all records starting from B1",
        }
    );
    await contains(".o_list_section_options:eq(2) button").click();
    await contains(".o-dropdown-item:contains(Delete)").click();
    expect(queryAllTexts(".o_data_row")).toEqual(["C", "r1", "r2", "A", "A1", "A2"], {
        message: "Deleting B will then remove all records starting from B1",
    });
});

test("add a section", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    expect(`.o_note_row`).toHaveCount(0);
    await contains(".o_field_x2many_list_row_add a:eq(1)").click();
    await edit("D");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
        "D",
    ]);
    expect(`.o_is_line_section`).toHaveCount(4);
});

test("add note", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    expect(`.o_note_row`).toHaveCount(0);
    await contains(".o_field_x2many_list_row_add a:last").click();
    await edit("this is a note");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
        "this is a note",
    ]);
    expect(`.o_is_line_note`).toHaveCount(1);
});

test("section_and_note_text widget", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name" widget="section_and_note_text"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    expect(`.o_note_row`).toHaveCount(0);
    await contains(".o_field_x2many_list_row_add a:last").click();
    expect(`.o_is_line_note textarea`).toHaveCount(1);
    await edit("this is a note\non 2 lines");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
        "this is a note\non 2 lines",
    ]);
});

test("sections with required content field", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name" required="1"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(".o_data_row").toHaveCount(13);
    await contains(".o_list_section_options:eq(0) button").click();
    await contains(".o-dropdown-item:contains(Add a subsection)").click();
    expect(".o_data_row").toHaveCount(14);
    await contains(".o_list_section_options:eq(1) button").click();
    await contains(".o-dropdown-item:contains(Delete)").click();
    expect(".o_data_row").toHaveCount(13);
    await contains(".o_list_section_options:eq(0) button").click();
    await contains(".o-dropdown-item:contains(Add a subsection)").click();
    expect(".o_invalid_cell").toHaveCount(0);
    await press("Enter");
    await animationFrame();
    expect(".o_invalid_cell").toHaveCount(1);
    expect(".o_data_row").toHaveCount(14);
    await contains(".o_form_button_cancel").click();
    expect(".o_data_row").toHaveCount(13);
    await contains(".o_field_x2many_list_row_add a:eq(1)").click();
    expect(".o_data_row").toHaveCount(14);
    expect(".o_invalid_cell").toHaveCount(0);
    await press("Enter");
    await animationFrame();
    expect(".o_invalid_cell").toHaveCount(1);
    await edit("D");
    await press("Enter");
    await animationFrame();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
        "D",
        "",
    ]);
});

test("sections duplicate with many2many", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="m2m" widget="many2many_tags"/>
                        <field name="sequence"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual(
        [
            "r1 \nValue 1\n 1",
            "r2 \nValue 2\n 2",
            "A",
            "A1 \nValue 1\nValue 3\n 4",
            "A2 \nValue 1\nValue 2\n 5",
            "B",
            "B1 \nValue 1\nValue 3\n 7",
            "B2 \n 8",
            "Ba",
            "Ba1 \nValue 2\nValue 3\n 10",
            "Ba2 \nValue 3\n 11",
            "C",
            "C1 \n 13",
        ],
        { message: "m2m values are not shown inside (sub-)section rows" }
    );
    await contains(".o_list_section_options:eq(1) button").click();
    await contains(".o-dropdown-item:contains(Duplicate)").click();
    expect(queryAllTexts(".o_data_row")).toEqual(
        [
            "r1 \nValue 1\n 1",
            "r2 \nValue 2\n 2",
            "A",
            "A1 \nValue 1\nValue 3\n 4",
            "A2 \nValue 1\nValue 2\n 5",
            "B",
            "B1 \nValue 1\nValue 3\n 7",
            "B2 \n 8",
            "Ba",
            "Ba1 \nValue 2\nValue 3\n 10",
            "Ba2 \nValue 3\n 11",
            "B",
            "B1 \nValue 1\nValue 3\n 13",
            "B2 \n 14",
            "Ba",
            "Ba1 \nValue 2\nValue 3\n 16",
            "Ba2 \nValue 3\n 17",
            "C",
            "C1 \n 19",
        ],
        { message: "m2m values are copied as well" }
    );
    await contains(".o_list_section_options:eq(2) button").click();
    await contains(".o-dropdown-item:contains(Duplicate)").click();
    expect(queryAllTexts(".o_data_row")).toEqual(
        [
            "r1 \nValue 1\n 1",
            "r2 \nValue 2\n 2",
            "A",
            "A1 \nValue 1\nValue 3\n 4",
            "A2 \nValue 1\nValue 2\n 5",
            "B",
            "B1 \nValue 1\nValue 3\n 7",
            "B2 \n 8",
            "Ba",
            "Ba1 \nValue 2\nValue 3\n 10",
            "Ba2 \nValue 3\n 11",
            "Ba",
            "Ba1 \nValue 2\nValue 3\n 13",
            "Ba2 \nValue 3\n 14",
            "B",
            "B1 \nValue 1\nValue 3\n 16",
            "B2 \n 17",
            "Ba",
            "Ba1 \nValue 2\nValue 3\n 19",
            "Ba2 \nValue 3\n 20",
            "C",
            "C1 \n 22",
        ],
        { message: "m2m values are copied as well" }
    );
});

test("swap sections and subsections", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        resId: 1,
        arch: `
            <form>
                <field
                    name="invoice_line_ids"
                    widget="section_and_note_one2many"
                    options="{'display_type_field': 'display_type', 'section_content_field': 'name', 'note_content_field': 'name'}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(2) button").click();
    await contains(".o-dropdown-item:contains(Add a subsection)").click();
    await edit("Bb");
    await contains(getFixture()).click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "A",
        "A1",
        "A2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "Bb",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(1) button").click();
    expect(".o-dropdown-item:contains(Move Down)").toHaveCount(1);
    expect(".o-dropdown-item:contains(Move Up)").toHaveCount(1);
    await contains(".o_list_section_options:eq(0) button").click();
    expect(".o-dropdown-item:contains(Move Down)").toHaveCount(1);
    expect(".o-dropdown-item:contains(Move Up)").toHaveCount(0);
    await contains(".o_list_section_options:eq(4) button").click();
    expect(".o-dropdown-item:contains(Move Down)").toHaveCount(0);
    expect(".o-dropdown-item:contains(Move Up)").toHaveCount(1);
    await contains(".o_list_section_options:eq(1) button").click();
    await contains(".o-dropdown-item:contains(Move Up)").click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "B",
        "B1",
        "B2",
        "Ba",
        "Ba1",
        "Ba2",
        "Bb",
        "A",
        "A1",
        "A2",
        "C",
        "C1",
    ]);
    await contains(".o_list_section_options:eq(1) button").click();
    expect(".o-dropdown-item:contains(Move Down)").toHaveCount(1);
    expect(".o-dropdown-item:contains(Move Up)").toHaveCount(0);
    await contains(".o_list_section_options:eq(2) button").click();
    expect(".o-dropdown-item:contains(Move Down)").toHaveCount(0);
    expect(".o-dropdown-item:contains(Move Up)").toHaveCount(1);
    await contains(".o_list_section_options:eq(1) button").click();
    await contains(".o-dropdown-item:contains(Move Down)").click();
    expect(queryAllTexts(".o_data_row")).toEqual([
        "r1",
        "r2",
        "B",
        "B1",
        "B2",
        "Bb",
        "Ba",
        "Ba1",
        "Ba2",
        "A",
        "A1",
        "A2",
        "C",
        "C1",
    ]);
});
