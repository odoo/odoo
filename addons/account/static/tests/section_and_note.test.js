import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Invoice extends models.Model {
    invoice_line_ids = fields.One2many({
        string: "Lines",
        relation: "invoice_line",
        relation_field: "invoice_id",
    });
    _records = [{ id: 1, invoice_line_ids: [1, 2, 3] }];
}

class InvoiceLine extends models.Model {
    _name = "invoice_line";

    sequence = fields.Integer();
    display_type = fields.Selection({
        string: "Type",
        selection: [
            ["line_section", "Section"],
            ["line_note", "Note"],
        ],
    });
    invoice_id = fields.Many2one({
        string: "Invoice",
        relation: "invoice",
    });
    name = fields.Text();
    price = fields.Monetary({ currency_field: "" });
    _records = [
        { id: 1, display_type: false, invoice_id: 1, name: "product\n2 lines", price: 123.45 },
        { id: 2, display_type: "line_section", invoice_id: 1, name: "section" },
        { id: 3, display_type: "line_note", invoice_id: 1, name: "note" },
    ];
}

defineModels([Invoice, InvoiceLine]);
defineMailModels();

test("correct display of section and note fields", async () => {
    await mountView({
        type: "form",
        resModel: "invoice",
        arch: `
            <form>
                <field name="invoice_line_ids" widget="section_and_note_one2many">
                    <list editable="bottom">
                        <field name="sequence" widget="handle"/>
                        <field name="display_type" column_invisible="1"/>
                        <field name="name" widget="section_and_note_text"/>
                        <field name="price"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect('[name="invoice_line_ids"] table').toHaveClass("o_section_and_note_list_view");
    expect("tr.o_data_row:nth-child(1)").not.toHaveClass("o_is_line_section", {
        message: "should not have a section class",
    });

    const sectionLine = queryOne("tr.o_data_row:nth-child(2)");
    const sectionCell = queryOne("td.o_section_and_note_text_cell", { root: sectionLine });
    expect(sectionLine).toHaveClass("o_is_line_section", {
        message: "should have a section class",
    });
    expect(sectionCell).toHaveAttribute("colspan", "2");

    const noteLine = queryOne("tr.o_data_row:nth-child(3)");
    const noteCell = queryOne("td.o_section_and_note_text_cell", { root: noteLine });
    expect(noteLine).toHaveClass("o_is_line_note", { message: "should have a note class" });
    expect(noteCell).toHaveAttribute("colspan", "2");

    await contains(noteCell).click();
    expect(queryAll('div[name="name"] textarea', { root: noteCell })).toHaveCount(1);
    await contains(sectionCell).click();
    expect(queryAll('div[name="name"] input', { root: sectionCell })).toHaveCount(1);

    // Drag and drop the second line in first position
    await contains("tbody tr:nth-child(2) .o_row_handle", { visible: false }).dragAndDrop(
        "tbody tr:nth-child(1)"
    );
    expect(queryAllTexts(".o_data_cell.o_list_text")).toEqual([
        "section",
        "product\n2 lines",
        "note",
    ]);
});
