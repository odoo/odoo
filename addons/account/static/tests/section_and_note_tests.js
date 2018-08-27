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
    QUnit.test('correct display of section and note fields', function (assert) {
        assert.expect(4);
        var form = createView({
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

        // section should be displayed correctly
        var $tr0 = form.$('tr.o_data_row:eq(0)');

        assert.strictEqual($tr0.hasClass('o_is_line_section'), false,
            "should not have a section class");

        var $tr1 = form.$('tr.o_data_row:eq(1)');

        assert.strictEqual($tr1.hasClass('o_is_line_section'), true,
            "should have a section class");

        // enter edit mode
        form.$buttons.find('.o_form_button_edit').click();

        // editing line should be textarea
        $tr0 = form.$('tr.o_data_row:eq(0)');
        $tr0.find('td.o_data_cell').click();
        assert.strictEqual($tr0.find('td.o_data_cell textarea[name="name"]').length, 1,
            "editing line should be textarea");

        // editing section should be input
        $tr1 = form.$('tr.o_data_row:eq(1)');
        $tr1.find('td.o_data_cell').click();
        assert.strictEqual($tr1.find('td.o_data_cell input[name="name"]').length, 1,
            "editing section should be input");

        form.destroy();
    });
});
});
