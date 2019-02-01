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
                    parent_id: {string: "Parent", type: "many2one", relation: 'partner'},
                    sibling_ids: {string: "Sibling", type: "many2many", relation: 'partner'},
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

    QUnit.module('FieldMany2One');

    QUnit.test("many2one in a mobile environment", async function (assert) {
        assert.expect(7);

        var form = await createView({
            View: FormView,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<field name="parent_id"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,kanban': '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div class="oe_kanban_global_click"><field name="display_name"/></div>' +
                    '</t></templates>' +
                '</kanban>',
                'partner,false,search': '<search></search>',
            },
            data: this.data,
            model: 'partner',
            res_id: 2,
            viewOptions: {mode: 'edit'},
        });

        var $input = form.$('.o_field_many2one input');

        assert.doesNotHaveClass($input, 'ui-autocomplete-input',
            "autocomplete should not be visible in a mobile environment");

        await testUtils.dom.click($input);

        var $modal = $('.o_modal_full .modal-lg');
        assert.equal($modal.length, 1, 'there should be one modal opened in full screen');
        assert.containsOnce($modal, '.o_kanban_view',
            'kanban view should be open in SelectCreateDialog');
        assert.containsOnce($modal, '.o_cp_searchview',
            'should have Search view inside SelectCreateDialog');
        assert.containsNone($modal.find(".o_control_panel .o_cp_buttons"), '.o-kanban-button-new',
            "kanban view in SelectCreateDialog should not have Create button");
        assert.strictEqual($modal.find(".o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").length, 3,
            "popup should load 3 records in kanban");

        await testUtils.dom.click($modal.find('.o_kanban_view .o_kanban_record:first'));

        assert.strictEqual($input.val(), 'first record',
            'clicking kanban card should select record for many2one field');
        form.destroy();
    });

    QUnit.test("hide/show element using selection_mode in kanban view in a mobile environment", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<field name="parent_id"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,kanban': '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div class="oe_kanban_global_click">' +
                            '<field name="display_name"/>' +
                        '</div>' +
                        '<div class="o_sibling_tags" t-if="!selection_mode">' +
                            '<field name="sibling_ids"/>' +
                        '</div>' +
                        '<div class="o_foo" t-if="selection_mode">' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
                'partner,false,search': '<search></search>',
            },
            data: this.data,
            model: 'partner',
            res_id: 2,
            viewOptions: {mode: 'edit'},
        });

        var $input = form.$('.o_field_many2one input');

        assert.doesNotHaveClass($input, 'ui-autocomplete-input',
            "autocomplete should not be visible in a mobile environment");

        await testUtils.dom.click($input);

        var $modal = $('.o_modal_full .modal-lg');
        assert.equal($modal.length, 1, 'there should be one modal opened in full screen');
        assert.containsOnce($modal, '.o_kanban_view',
            'kanban view should be open in SelectCreateDialog');
        assert.containsNone($modal, '.o_kanban_view .o_sibling_tags',
            'o_sibling_tags div should not be available as div have condition on selection_mode');
        assert.containsN($modal, '.o_kanban_view .o_foo', 3,
            'o_foo div should be available as div have condition on selection_mode');

        form.destroy();
    });

    QUnit.test("kanban_view_ref attribute opens specific kanban view given as a reference in a mobile environment", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<field name="parent_id" kanban_view_ref="2"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,1,kanban': '<kanban class="kanban1">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div class="oe_kanban_global_click">' +
                            '<field name="display_name"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
                'partner,2,kanban': '<kanban class="kanban2">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div class="oe_kanban_global_click">' +
                            '<div>' +
                                '<field name="display_name"/>' +
                            '</div>' +
                            '<div>' +
                                '<field name="trululu"/>' +
                            '</div>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
                'partner,false,search': '<search></search>',
            },
            data: this.data,
            model: 'partner',
            res_id: 2,
            viewOptions: {mode: 'edit'},
        });

        var $input = form.$('.o_field_many2one input');

        assert.doesNotHaveClass($input, 'ui-autocomplete-input',
            "autocomplete should not be visible in a mobile environment");

        await testUtils.dom.click($input);

        var $modal = $('.o_modal_full .modal-lg');
        assert.equal($modal.length, 1, 'there should be one modal opened in full screen');
        assert.containsOnce($modal, '.o_kanban_view',
            'kanban view should be open in SelectCreateDialog');
        assert.hasClass($modal.find('.o_kanban_view'), 'kanban2',
            'kanban view with id 2 should be opened as it is given as kanban_view_ref');
        assert.strictEqual($modal.find('.o_kanban_view .o_kanban_record:first').text(),
            'first recordaaa',
            'kanban with two fields should be opened');

        form.destroy();
    });

    QUnit.module('FieldMany2Many');

    QUnit.test("many2many_tags in a mobile environment", async function (assert) {
        assert.expect(10);

        var rpcReadCount = 0;

        var form = await createView({
            View: FormView,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<field name="sibling_ids" widget="many2many_tags"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,kanban': '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div class="oe_kanban_global_click"><field name="display_name"/></div>' +
                    '</t></templates>' +
                '</kanban>',
                'partner,false,search': '<search></search>',
            },
            data: this.data,
            model: 'partner',
            res_id: 2,
            viewOptions: {mode: 'edit'},
            mockRPC: function (route, args) {
                if (args.method === "read" && args.model === "partner") {
                    if (rpcReadCount === 0) {
                        assert.deepEqual(args.args[0], [2], "form should initially show partner 2");
                    } else if (rpcReadCount === 1) {
                        assert.deepEqual(args.args[0], [1], "partner with id 1 should be selected");
                    }
                    rpcReadCount++;
                }
                return this._super.apply(this, arguments);
            },
        });

        var $input = form.$(".o_field_widget .o_input");

        assert.strictEqual($input.find(".badge").length, 0,
            "many2many_tags should have no tags");

        await testUtils.dom.click($input);

        var $modal = $('.o_modal_full .modal-lg');
        assert.equal($modal.length, 1, 'there should be one modal opened in full screen');
        assert.containsOnce($modal, '.o_kanban_view',
            'kanban view should be open in SelectCreateDialog');
        assert.containsOnce($modal, '.o_cp_searchview',
            'should have Search view inside SelectCreateDialog');
        assert.containsNone($modal.find(".o_control_panel .o_cp_buttons"), '.o-kanban-button-new',
            "kanban view in SelectCreateDialog should not have Create button");
        assert.strictEqual($modal.find(".o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").length, 3,
            "popup should load 3 records in kanban");

        await testUtils.dom.click($modal.find('.o_kanban_view .o_kanban_record:first'));

        assert.strictEqual(rpcReadCount, 2, "there should be a read for current form record and selected sibling");
        assert.strictEqual(form.$(".o_field_widget.o_input .badge").length, 1,
            "many2many_tags should have partner coucou3");

        form.destroy();
    });

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
