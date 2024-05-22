odoo.define('account.section_and_note_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var createView = testUtils.createView;

QUnit.module('section_and_note', {
    beforeEach: function () {
        this.data = {
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
                    {id: 1, invoice_line_ids: [1, 2]},
                ],
            },
            invoice_line: {
                fields: {
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
                },
                records: [
                    {id: 1, display_type: false, invoice_id: 1, name: 'product\n2 lines'},
                    {id: 2, display_type: 'line_section', invoice_id: 1, name: 'section'},
                ]
            },
        };
    },
}, function () {
    QUnit.test('correct display of section and note fields', async function (assert) {
        assert.expect(5);
        var form = await createView({
            View: FormView,
            model: 'invoice',
            data: this.data,
            arch: '<form>' +
                    '<field name="invoice_line_ids" widget="section_and_note_one2many"/>' +
                '</form>',
            archs: {
                'invoice_line,false,list': '<tree editable="bottom">' +
                    '<field name="display_type" invisible="1"/>' +
                    '<field name="name" widget="section_and_note_text"/>' +
                '</tree>',
            },
            res_id: 1,
        });

        assert.hasClass(form.$('[name="invoice_line_ids"] table'), 'o_section_and_note_list_view');

        // section should be displayed correctly
        var $tr0 = form.$('tr.o_data_row:eq(0)');

        assert.doesNotHaveClass($tr0, 'o_is_line_section',
            "should not have a section class");

        var $tr1 = form.$('tr.o_data_row:eq(1)');

        assert.hasClass($tr1, 'o_is_line_section',
            "should have a section class");

        // enter edit mode
        await testUtils.form.clickEdit(form);

        // editing line should be textarea
        $tr0 = form.$('tr.o_data_row:eq(0)');
        await testUtils.dom.click($tr0.find('td.o_data_cell'));
        assert.containsOnce($tr0, 'td.o_data_cell textarea[name="name"]',
            "editing line should be textarea");

        // editing section should be input
        $tr1 = form.$('tr.o_data_row:eq(1)');
        await testUtils.dom.click($tr1.find('td.o_data_cell'));
        assert.containsOnce($tr1, 'td.o_data_cell input[name="name"]',
            "editing section should be input");

        form.destroy();
    });
});
});
