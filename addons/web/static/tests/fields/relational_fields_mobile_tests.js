odoo.define('web.relational_fields_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('relational_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    bar: {string: "Bar", type: "boolean", default: true},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1] },
                    p: {string: "one2many field", type: "one2many", relation: 'partner', relation_field: 'trululu'},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    partner_ids: {string: "many2many field", type: "many2many", relation: 'partner'},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    bar: true,
                    foo: "yop",
                    int_field: 10,
                    qux: 0.44,
                    p: [],
                    trululu: 4,
                }, {
                    id: 2,
                    display_name: "second record",
                    bar: true,
                    foo: "blip",
                    int_field: 9,
                    qux: 13,
                    p: [],
                    trululu: 1,
                }, {
                    id: 4,
                    display_name: "aaa",
                    bar: false,
                }],
                onchanges: {},
            },
        };
    }
}, function () {

    QUnit.module('FieldOne2Many');

    QUnit.test('one2many kanban: deletion in mobile', async function (assert) {
        assert.expect(9);

        this.data.partner.records[0].p = [1, 2];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="p">' +
                        '<kanban>' +
                            '<templates>' +
                                '<t t-name="kanban-box">' +
                                    '<div class="oe_kanban_global_click">' +
                                        '<field name="display_name"/>' +
                                    '</div>' +
                                '</t>' +
                            '</templates>' +
                        '</kanban>' +
                        '<form string="Partners">' +
                            '<field name="display_name"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    var commands = args.args[1].p;
                    assert.strictEqual(commands.length, 2,
                        'should have generated two commands');
                    assert.ok(commands[0][0] === 4 && commands[0][1] === 2,
                        'should have generated the command 2 (DELETE) with id 1');
                    assert.ok(commands[1][0] === 2 && commands[1][1] === 1,
                        'should have generated the command 2 (DELETE) with id 2');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsNone(form, '.o_field_one2many .o-kanban-button-new',
            '"Create" button should not be visible in readonly');

        await testUtils.form.clickEdit(form);

        assert.containsOnce(form, '.o_field_one2many .o-kanban-button-new',
            '"Create" button should be visible in edit');
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 2,
            "should have 2 records");

        // open and delete record
        await testUtils.dom.click(form.$('.oe_kanban_global_click').first());
        assert.strictEqual($('.modal .modal-footer .o_btn_remove').length, 1,
            'there should be a Remove button in the modal footer');
        await testUtils.dom.click($('.modal .modal-footer .o_btn_remove'));
        assert.strictEqual($('.o_modal').length, 0, "there shoul be no more modal");
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 1,
            'should contain 1 records');

        // save and check that the correct command has been generated
        await testUtils.form.clickSave(form);
        form.destroy();
    });

    QUnit.module('FieldMany2Many');

    QUnit.test('many2many kanban: deletion in mobile', async function (assert) {
        assert.expect(8);
        this.data.partner.records[0].partner_ids = [2, 4];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="partner_ids">' +
                        '<kanban>' +
                        '<field name="display_name"/>' +
                            '<templates>' +
                                '<t t-name="kanban-box">' +
                                    '<div class="oe_kanban_global_click">' +
                                        '<span><t t-esc="record.display_name.value"/></span>' +
                                    '</div>' +
                                '</t>' +
                            '</templates>' +
                        '</kanban>' +
                        '<form string="Partners">' +
                            '<field name="display_name"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    var commands = args.args[1].partner_ids;
                    assert.strictEqual(commands.length, 1,
                        'should have generated one commands');
                    assert.deepEqual(commands[0], [6, false, [4]] ,
                        'should properly write ids');
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.containsNone(form.$('.o_field_many2many .o-kanban-button-new'),
            '"Add" button should not be visible in readonly');
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.o_field_many2many .o-kanban-button-new',
            '"Add" button should be visible in edit');
        assert.containsN(form, '.o_kanban_record:not(.o_kanban_ghost)', 2,
            "should have 2 records");
        // open and delete record
        await testUtils.dom.click(form.$('.oe_kanban_global_click').first());
        assert.strictEqual($('.modal .modal-footer .o_btn_remove').length, 1,
            'there should be a modal having "Remove" Button');
        await testUtils.dom.click($('.modal .modal-footer .o_btn_remove'));
        assert.containsNone($('.o_modal'), "modal should have been closed");
        assert.containsOnce(form, '.o_kanban_record:not(.o_kanban_ghost)',
            'should contain 1 records');
         // save and check that the correct command has been generated
        await testUtils.form.clickSave(form);
        form.destroy();
    });
});
});
});
