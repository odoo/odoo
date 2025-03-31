/** @odoo-module **/

import {
    click,
    dragAndDrop,
    getNodesTextContent,
    getFixture,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module('section_and_note', (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                invoice: {
                    fields: {
                        invoice_line_ids: {
                            string: "Lines",
                            type: 'one2many',
                            relation: 'invoice_line',
                            relation_field: 'invoice_id'
                        },
                    },
                    records: [
                        {id: 1, invoice_line_ids: [1, 2, 3]},
                    ],
                },
                invoice_line: {
                    fields: {
                        sequence: { string: "sequence", type: "integer", sortable: true },
                        display_type: {
                            string: 'Type',
                            type: 'selection',
                            selection: [['line_section', "Section"], ['line_note', "Note"]]
                        },
                        invoice_id: {
                            string: "Invoice",
                            type: 'many2one',
                            relation: 'invoice'
                        },
                        name: {
                            string: "Name",
                            type: 'text'
                        },
                        price: {
                            string: "Price",
                            type: 'monetary',
                        }
                    },
                    records: [
                        {id: 1, display_type: false, invoice_id: 1, name: 'product\n2 lines', price: 123.45},
                        {id: 2, display_type: 'line_section', invoice_id: 1, name: 'section'},
                        {id: 3, display_type: 'line_note', invoice_id: 1, name: 'note'},
                    ]
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.test('correct display of section and note fields', async (assert) => {
        assert.expect(9);
        await makeView({
            type: 'form',
            resModel: 'invoice',
            serverData,
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

        assert.hasClass(target.querySelector('[name="invoice_line_ids"] table'), 'o_section_and_note_list_view');

        // product should be displayed correctly
        assert.doesNotHaveClass(target.querySelector('tr.o_data_row:nth-child(1'), 'o_is_line_section',
            "should not have a section class");

        // section should be displayed correctly
        const section_line = target.querySelector('tr.o_data_row:nth-child(2)');
        const section_cell = section_line.querySelector('td.o_section_and_note_text_cell');
        assert.hasClass(section_line, 'o_is_line_section',
            "should have a section class");
        assert.hasAttrValue(section_cell, 'colspan', '2')

        // note should be displayed correctly
        const note_line = target.querySelector('tr.o_data_row:nth-child(3)');
        const note_cell = note_line.querySelector('td.o_section_and_note_text_cell');
        assert.hasClass(note_line, 'o_is_line_note',
            "should have a note class");
        assert.hasAttrValue(note_cell, 'colspan', '2')

        // editing note line should be textarea
        await click(note_cell);
        assert.containsOnce(note_line, 'td.o_section_and_note_text_cell div[name="name"] textarea',
            "note line should be textarea");

        // editing section line should be input
        await click(section_cell);
        assert.containsOnce(section_line, 'td.o_section_and_note_text_cell div[name="name"] input',
            "section line should be input");

        // Drag and drop the second line in first position
        await dragAndDrop("tbody tr:nth-child(2) .o_row_handle", "tbody tr:nth-child(1)");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell.o_list_text")),
            ["section", "product\n2 lines", "note"]
        );
    });
});
