odoo.define('web.basic_fields_tests', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var session = require('web.session');
var testUtils = require('web.test_utils');
var field_registry = require('web.field_registry');

var createView = testUtils.createView;
var createView = testUtils.createView;
var DebouncedField = basicFields.DebouncedField;
var JournalDashboardGraph = basicFields.JournalDashboardGraph;
var _t = core._t;

QUnit.module('fields', {}, function () {

QUnit.module('basic_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    date: {string: "A date", type: "date", searchable: true},
                    datetime: {string: "A datetime", type: "datetime", searchable: true},
                    display_name: {string: "Displayed name", type: "char", searchable: true},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", searchable: true, trim: true},
                    bar: {string: "Bar", type: "boolean", default: true, searchable: true},
                    txt: {string: "txt", type: "text", default: "My little txt Value\nHo-ho-hoooo Merry Christmas"},
                    int_field: {string: "int_field", type: "integer", sortable: true, searchable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1], searchable: true},
                    p: {string: "one2many field", type: "one2many", relation: 'partner', searchable: true},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner', searchable: true},
                    timmy: {string: "pokemon", type: "many2many", relation: 'partner_type', searchable: true},
                    product_id: {string: "Product", type: "many2one", relation: 'product', searchable: true},
                    sequence: {type: "integer", string: "Sequence", searchable: true},
                    currency_id: {string: "Currency", type: "many2one", relation: "currency", searchable: true},
                    selection: {string: "Selection", type: "selection", searchable:true,
                        selection: [['normal', 'Normal'],['blocked', 'Blocked'],['done', 'Done']]},
                    document: {string: "Binary", type: "binary"},
                },
                records: [{
                    id: 1,
                    date: "2017-02-03",
                    datetime: "2017-02-08 10:00:00",
                    display_name: "first record",
                    bar: true,
                    foo: "yop",
                    int_field: 10,
                    qux: 0.44444,
                    p: [],
                    timmy: [],
                    trululu: 4,
                    selection: 'blocked',
                    document: 'coucou==\n',
                }, {
                    id: 2,
                    display_name: "second record",
                    bar: true,
                    foo: "blip",
                    int_field: 0,
                    qux: 0,
                    p: [],
                    timmy: [],
                    trululu: 1,
                    sequence: 4,
                    currency_id: 2,
                    selection: 'normal',
                }, {
                    id: 4,
                    display_name: "aaa",
                    foo: "abc",
                    sequence: 9,
                    int_field: false,
                    qux: false,
                    selection: 'done',
                },
                {id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859, m2o: 1, m2m: []},
                {id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, m2o: 1, m2m: [1], currency_id: 1}],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char", searchable: true}
                },
                records: [{
                    id: 37,
                    display_name: "xphone",
                }, {
                    id: 41,
                    display_name: "xpad",
                }]
            },
            partner_type: {
                fields: {
                    name: {string: "Partner Type", type: "char", searchable: true},
                    color: {string: "Color index", type: "integer", searchable: true},
                },
                records: [
                    {id: 12, display_name: "gold", color: 2},
                    {id: 14, display_name: "silver", color: 5},
                ]
            },
            currency: {
                fields: {
                    symbol: {string: "Currency Sumbol", type: "char", searchable: true},
                    position: {string: "Currency Position", type: "char", searchable: true},
                },
                records: [{
                    id: 1,
                    display_name: "$",
                    symbol: "$",
                    position: "before",
                }, {
                    id: 2,
                    display_name: "€",
                    symbol: "€",
                    position: "after",
                }]
            },
        };
    }
}, function () {

    QUnit.module('DebouncedField');

    QUnit.test('debounced fields do not trigger call _setValue once destroyed', async function (assert) {
        assert.expect(4);

        var def = testUtils.makeTestPromise();
        var _doAction = DebouncedField.prototype._doAction;
        DebouncedField.prototype._doAction = function () {
            _doAction.apply(this, arguments);
            def.resolve();
        };
        var _setValue = DebouncedField.prototype._setValue;
        DebouncedField.prototype._setValue = function () {
            assert.step('_setValue');
            _setValue.apply(this, arguments);
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            fieldDebounce: 3,
            viewOptions: {
                mode: 'edit',
            },
        });

        // change the value
        testUtils.fields.editInput(form.$('input[name=foo]'), 'new value');
        assert.verifySteps([], "_setValue shouldn't have been called yet");

        // save
        await testUtils.form.clickSave(form);
        assert.verifySteps(['_setValue'], "_setValue should have been called once");

        // destroy the form view
        def = testUtils.makeTestPromise();
        form.destroy();
        await testUtils.nextMicrotaskTick();

        // wait for the debounced callback to be called
        assert.verifySteps([],
            "_setValue should not have been called after widget destruction");

        DebouncedField.prototype._doAction = _doAction;
        DebouncedField.prototype._setValue = _setValue;
    });

    QUnit.module('FieldBoolean');

    QUnit.test('boolean field in form view', async function (assert) {
        assert.expect(13);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><label for="bar" string="Awesome checkbox"/><field name="bar"/></form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.o_field_boolean input:checked',
            "checkbox should be checked");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.o_field_boolean input:checked',
            "checkbox should still be checked");

        // uncheck the checkbox
        await testUtils.dom.click(form.$('.o_field_boolean input:checked'));
        assert.containsNone(form, '.o_field_boolean input:checked',
            "checkbox should no longer be checked");

        // save
        await testUtils.form.clickSave(form);
        assert.containsNone(form, '.o_field_boolean input:checked',
            "checkbox should still no longer be checked");

        // switch to edit mode and test the opposite change
        await testUtils.form.clickEdit(form);
        assert.containsNone(form, '.o_field_boolean input:checked',
            "checkbox should still be unchecked");

        // check the checkbox
        await testUtils.dom.click(form.$('.o_field_boolean input'));
        assert.containsOnce(form, '.o_field_boolean input:checked',
            "checkbox should now be checked");

        // uncheck it back
        await testUtils.dom.click(form.$('.o_field_boolean input'));
        assert.containsNone(form, '.o_field_boolean input:checked',
            "checkbox should now be unchecked");

        // check the checkbox by clicking on label
        await testUtils.dom.click(form.$('.o_form_view label:first'));
        assert.containsOnce(form, '.o_field_boolean input:checked',
            "checkbox should now be checked");

        // uncheck it back
        await testUtils.dom.click(form.$('.o_form_view label:first'));
        assert.containsNone(form, '.o_field_boolean input:checked',
            "checkbox should now be unchecked");

        // check the checkbox by hitting the "enter" key after focusing it
        await testUtils.dom.triggerEvents(form.$('.o_field_boolean input'), [
            "focusin",
            {type: "keydown", which: $.ui.keyCode.ENTER},
            {type: "keyup", which: $.ui.keyCode.ENTER}]);
        assert.containsOnce(form, '.o_field_boolean input:checked',
        "checkbox should now be checked");
        // blindly press enter again, it should uncheck the checkbox
        $(document.activeElement).trigger({type: "keydown", which: $.ui.keyCode.ENTER});
        assert.containsNone(form, '.o_field_boolean input:checked',
        "checkbox should not be checked");
        await testUtils.nextTick();
        // blindly press enter again, it should check the checkbox back
        $(document.activeElement).trigger({type: "keydown", which: $.ui.keyCode.ENTER});
        assert.containsOnce(form, '.o_field_boolean input:checked',
            "checkbox should still be checked");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.o_field_boolean input:checked',
            "checkbox should still be checked");
        form.destroy();
    });

    QUnit.test('boolean field in editable list view', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="bar"/></tree>',
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input').length, 5,
            "should have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input:checked').length, 4,
            "should have 4 checked input");

        // Edit a line
        var $cell = list.$('tr.o_data_row:has(.custom-checkbox input:checked) td:not(.o_list_record_selector)').first();
        assert.ok($cell.find('.custom-checkbox input:checked').prop('disabled'),
            "input should be disabled in readonly mode");
        await testUtils.dom.click($cell);
        assert.ok(!$cell.find('.custom-checkbox input:checked').prop('disabled'),
            "input should not have the disabled property in edit mode");
        await testUtils.dom.click($cell.find('.custom-checkbox input:checked'));

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        $cell = list.$('tr.o_data_row:has(.custom-checkbox input:not(:checked)) td:not(.o_list_record_selector)').first();
        assert.ok($cell.find('.custom-checkbox input:not(:checked)').prop('disabled'),
            "input should be disabled again");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input').length, 5,
            "should still have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input:checked').length, 3,
            "should now have only 3 checked input");

        // Re-Edit the line and fake-check the checkbox
        await testUtils.dom.click($cell);
        await testUtils.dom.click($cell.find('.custom-checkbox input'));
        await testUtils.dom.click($cell.find('.custom-checkbox input'));

        // Save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input').length, 5,
            "should still have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input:checked').length, 3,
            "should still have only 3 checked input");

        // Re-Edit the line to check the checkbox back but this time click on
        // the checkbox directly in readonly mode !
        $cell = list.$('tr.o_data_row:has(.custom-checkbox input:not(:checked)) td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell.find('.custom-checkbox .custom-control-label'));

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input').length, 5,
            "should still have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .custom-checkbox input:checked').length, 4,
            "should now have 4 checked input back");
        list.destroy();
    });

    QUnit.module('FieldBooleanToggle');

    QUnit.test('use boolean toggle widget in form view', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="bar" widget="boolean_toggle"/></form>',
            res_id: 2,
        });

        assert.containsOnce(form, ".custom-checkbox.o_boolean_toggle", "Boolean toggle widget applied to boolean field");
        form.destroy();
    });

    QUnit.module('FieldToggleButton');

    QUnit.test('use toggle_button in list view', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree>' +
                    '<field name="bar" widget="toggle_button" ' +
                        'options="{&quot;active&quot;: &quot;Reported in last payslips&quot;, &quot;inactive&quot;: &quot;To Report in Payslip&quot;}"/>' +
                '</tree>',
        });

        assert.containsN(list, 'button i.fa.fa-circle.o_toggle_button_success', 4,
            "should have 4 green buttons");
        assert.containsOnce(list, 'button i.fa.fa-circle.text-muted',
            "should have 1 muted button");

        assert.hasAttrValue(list.$('.o_list_view button').first(), 'title',
            "Reported in last payslips", "active buttons should have proper tooltip");
        assert.hasAttrValue(list.$('.o_list_view button').last(), 'title',
            "To Report in Payslip", "inactive buttons should have proper tooltip");

        // clicking on first button to check the state is properly changed
        await testUtils.dom.click(list.$('.o_list_view button').first());
        assert.containsN(list, 'button i.fa.fa-circle.o_toggle_button_success', 3,
            "should have 3 green buttons");

        await testUtils.dom.click(list.$('.o_list_view button').first());
        assert.containsN(list, 'button i.fa.fa-circle.o_toggle_button_success', 4,
            "should have 4 green buttons");
        list.destroy();
    });

    QUnit.test('toggle_button in form view (edit mode)', async function (assert) {
        assert.expect(6);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="bar" widget="toggle_button" ' +
                        'options="{\'active\': \'Active value\', \'inactive\': \'Inactive value\'}"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.step('write');
                }
                return this._super.apply(this, arguments);
            },
            res_id: 2,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=bar] i.o_toggle_button_success:not(.text-muted)').length,
            1, "should be green");

        // click on the button to toggle the value
        await testUtils.dom.click(form.$('.o_field_widget[name=bar]'));

        assert.strictEqual(form.$('.o_field_widget[name=bar] i.text-muted:not(.o_toggle_button_success)').length,
            1, "should be gray");
        assert.verifySteps([]);

        // save
        await testUtils.form.clickSave(form);

        assert.strictEqual(form.$('.o_field_widget[name=bar] i.text-muted:not(.o_toggle_button_success)').length,
            1, "should still be gray");
        assert.verifySteps(['write']);

        form.destroy();
    });

    QUnit.test('toggle_button in form view (readonly mode)', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="bar" widget="toggle_button" ' +
                        'options="{\'active\': \'Active value\', \'inactive\': \'Inactive value\'}"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.step('write');
                }
                return this._super.apply(this, arguments);
            },
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_field_widget[name=bar] i.o_toggle_button_success:not(.text-muted)').length,
            1, "should be green");

        // click on the button to toggle the value
        await testUtils.dom.click(form.$('.o_field_widget[name=bar]'));

        assert.strictEqual(form.$('.o_field_widget[name=bar] i.text-muted:not(.o_toggle_button_success)').length,
            1, "should be gray");
        assert.verifySteps(['write']);

        form.destroy();
    });

    QUnit.module('FieldFloat');

    QUnit.test('float field when unset', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                    '<field name="qux" digits="[5,3]"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 4,
        });

        assert.doesNotHaveClass(form.$('.o_field_widget'), 'o_field_empty',
        'Non-set float field should be considered as 0.');
        assert.strictEqual(form.$('.o_field_widget').text(), "0.000",
        'Non-set float field should be considered as 0.');

        form.destroy();
    });

    QUnit.test('float fields use correct digit precision', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('span.o_field_number:contains(0.4)').length, 1,
                            "should contain a number rounded to 1 decimal");
        form.destroy();
    });

    QUnit.test('float field in form view', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="float" digits="[5,3]"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.doesNotHaveClass(form.$('.o_field_widget'), 'o_field_empty',
            'Float field should be considered set for value 0.');
        assert.strictEqual(form.$('.o_field_widget').first().text(), '0.000',
            'The value should be displayed properly.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('input[name=qux]').val(), '0.000',
            'The value should be rendered with correct precision.');

        await testUtils.fields.editInput(form.$('input[name=qux]'), '108.2458938598598');
        assert.strictEqual(form.$('input[name=qux]').val(), '108.2458938598598',
            'The value should not be formated yet.');

        await testUtils.fields.editInput(form.$('input[name=qux]'), '18.8958938598598');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '18.896',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('float field using formula in form view', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="float" digits="[5,3]"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        // Test computation with priority of operation
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('input[name=qux]'), '=20+3*2');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '26.000',
            'The new value should be calculated properly.');

        // Test computation with ** operand
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('input[name=qux]'), '=2**3');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '8.000',
            'The new value should be calculated properly.');

        // Test computation with ^ operant which should do the same as **
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('input[name=qux]'), '=2^3');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '8.000',
            'The new value should be calculated properly.');

        // Test computation and rounding
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('input[name=qux]'), '=100/3');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '33.333',
            'The new value should be calculated properly.');

        form.destroy();
    });

    QUnit.test('float field using incorrect formula in form view', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="float" digits="[5,3]"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        // Test that incorrect value is not computed
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('input[name=qux]'), '=abc');
        await testUtils.form.clickSave(form);
        assert.hasClass(form.$('.o_form_view'),'o_form_editable',
            "form view should still be editable");
        assert.hasClass(form.$('input[name=qux]'),'o_field_invalid',
            "fload field should be displayed as invalid");

        await testUtils.fields.editInput(form.$('input[name=qux]'), '=3:2?+4');
        await testUtils.form.clickSave(form);
        assert.hasClass(form.$('.o_form_view'),'o_form_editable',
            "form view should still be editable");
        assert.hasClass(form.$('input[name=qux]'),'o_field_invalid',
            "float field should be displayed as invalid");

        form.destroy();
    });

    QUnit.test('float field in editable list view', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="qux" widget="float" digits="[5,3]"/>' +
                  '</tree>',
        });

        var zeroValues = list.$('td.o_data_cell').filter(function () {return $(this).text() === '';});
        assert.strictEqual(zeroValues.length, 1,
            'Unset float values should be rendered as empty strings.');

        // switch to edit mode
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);

        assert.containsOnce(list, 'input[name="qux"]',
            'The view should have 1 input for editable float.');

        await testUtils.fields.editInput(list.$('input[name="qux"]'), '108.2458938598598');
        assert.strictEqual(list.$('input[name="qux"]').val(), '108.2458938598598',
            'The value should not be formated yet.');

        await testUtils.fields.editInput(list.$('input[name="qux"]'), '18.8958938598598');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('.o_field_widget').first().text(), '18.896',
            'The new value should be rounded properly.');

        list.destroy();
    });

    QUnit.test('do not trigger a field_changed if they have not changed', async function (assert) {
        assert.expect(2);

        this.data.partner.records[1].qux = false;
        this.data.partner.records[1].int_field = false;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="float" digits="[5,3]"/>' +
                        '<field name="int_field"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            }
        });

        await testUtils.form.clickEdit(form);
        await testUtils.form.clickSave(form);

        assert.verifySteps(['read']); // should not have save as nothing changed

        form.destroy();
    });

    QUnit.test('float widget on monetary field', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.monetary = {string: "Monetary", type: 'monetary'};
        this.data.partner.records[0].monetary = 9.99;
        this.data.partner.records[0].currency_id = 1;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="monetary" widget="float"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=monetary]').text(), '9.99',
            'value should be correctly formatted (with the float formatter)');

        form.destroy();
    });

    QUnit.test('float field with monetary widget and decimal precision', async function (assert) {
        assert.expect(5);

        this.data.partner.records = [{
            id: 1,
            qux: -8.89859,
            currency_id: 1,
        }];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="monetary" options="{\'field_digits\': True}"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '$\u00a0-8.9',
            'The value should be displayed properly.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '-8.9',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').parent().children().first().text(), '$',
            'The input should be preceded by a span containing the currency symbol.');

        await testUtils.fields.editInput(form.$('.o_field_monetary input'), '109.2458938598598');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '109.2458938598598',
            'The value should not be formated yet.');

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '$\u00a0109.2',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('float field with type number option', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                '<field name="qux" options="{\'type\': \'number\'}"/>' +
            '</form>',
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.ok(form.$('.o_field_widget')[0].hasAttribute('type'),
            'Float field with option type must have a type attribute.');
        assert.hasAttrValue(form.$('.o_field_widget'), 'type', 'number',
            'Float field with option type must have a type attribute equals to "number".');
        await testUtils.fields.editInput(form.$('input[name=qux]'), '123456.7890');
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget').val(), '123456.789',
            'Float value must be not formatted if input type is number.');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').text(), '123,456.8',
            'Float value must be formatted in readonly view even if the input type is number.');

        form.destroy();
    });

    QUnit.test('float field without type number option', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                '<field name="qux"/>' +
            '</form>',
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.hasAttrValue(form.$('.o_field_widget'), 'type', 'text',
            'Float field with option type must have a text type (default type).');

        await testUtils.fields.editInput(form.$('input[name=qux]'), '123456.7890');
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget').val(), '123,456.8',
            'Float value must be formatted if input type isn\'t number.');

        form.destroy();
    });


    QUnit.module('FieldEmail');

    QUnit.test('email field in form view', async function (assert) {
        assert.expect(7);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="email"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        var $mailtoLink = form.$('a.o_form_uri.o_field_widget.o_text_overflow');
        assert.strictEqual($mailtoLink.length, 1,
            "should have a anchor with correct classes");
        assert.strictEqual($mailtoLink.text(), 'yop',
            "the value should be displayed properly");
        assert.hasAttrValue($mailtoLink, 'href', 'mailto:yop',
            "should have proper mailto prefix");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, 'input[type="text"].o_field_widget',
            "should have an input for the email field");
        assert.strictEqual(form.$('input[type="text"].o_field_widget').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        await testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), 'new');

        // save
        await testUtils.form.clickSave(form);
        $mailtoLink = form.$('a.o_form_uri.o_field_widget.o_text_overflow');
        assert.strictEqual($mailtoLink.text(), 'new',
            "new value should be displayed properly");
        assert.hasAttrValue($mailtoLink, 'href', 'mailto:new',
            "should still have proper mailto prefix");

        form.destroy();
    });

    QUnit.test('email field in editable list view', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"  widget="email"/></tree>',
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').length, 5,
            "should have 5 cells");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yop',
            "value should be displayed properly as text");

        var $mailtoLink = list.$('a.o_form_uri.o_field_widget.o_text_overflow');
        assert.strictEqual($mailtoLink.length, 5,
            "should have anchors with correct classes");
        assert.hasAttrValue($mailtoLink.first(), 'href', 'mailto:yop',
            "should have proper mailto prefix");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(),'o_selected_row', 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        await testUtils.fields.editInput($cell.find('input'), 'new');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($cell.parent(), 'o_selected_row', 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'new',
            "value should be properly updated");
        $mailtoLink = list.$('a.o_form_uri.o_field_widget.o_text_overflow');
        assert.strictEqual($mailtoLink.length, 5,
            "should still have anchors with correct classes");
        assert.hasAttrValue($mailtoLink.first(), 'href', 'mailto:new',
            "should still have proper mailto prefix");

        list.destroy();
    });


    QUnit.module('FieldChar');

    QUnit.test('char widget isValid method works', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.required = true;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        var charField = _.find(form.renderer.allFieldWidgets)[0];
        assert.strictEqual(charField.isValid(), true);
        form.destroy();
    });

    QUnit.test('char field in form view', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget').text(), 'yop',
            "the value should be displayed properly");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, 'input[type="text"].o_field_widget',
            "should have an input for the char field");
        assert.strictEqual(form.$('input[type="text"].o_field_widget').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        await testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), 'limbo');

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').text(), 'limbo',
            'the new value should be displayed');
        form.destroy();
    });

    QUnit.test('setting a char field to empty string is saved as a false value', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {mode: 'edit'},
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual(args.args[1].foo, false,
                        'the foo value should be false');
                }
                return this._super.apply(this, arguments);
            }
        });

        await testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), '');

        // save
        await testUtils.form.clickSave(form);
        form.destroy();
    });

    QUnit.test('char field with size attribute', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.size = 5; // max length
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<group><field name="foo"/></group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.hasAttrValue(form.$('input.o_field_widget'), 'maxlength', '5',
            "maxlength attribute should have been set correctly on the input");

        form.destroy();
    });

    QUnit.test('char field in editable list view', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').length, 5,
            "should have 5 cells");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yop',
            "value should be displayed properly as text");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(),'o_selected_row', 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        await testUtils.fields.editInput($cell.find('input'), 'brolo');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($cell.parent(), 'o_selected_row', 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'brolo',
            "value should be properly updated");
        list.destroy();
    });

    QUnit.test('char field translatable', async function (assert) {
        assert.expect(3);

        this.data.partner.fields.foo.translate = true;

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_button" && args.method === 'translate_fields') {
                    assert.deepEqual(args.args, ["partner",1,"foo"], 'should call "call_button" route');
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.form.clickEdit(form);
        var $button = form.$('input[type="text"].o_field_char + .o_field_translate');
        assert.strictEqual($button.length, 1, "should have a translate button");
        await testUtils.dom.click($button);
        form.destroy();

        form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });
        $button = form.$('input[type="text"].o_field_char + .o_field_translate');
        assert.strictEqual($button.length, 0, "should not have a translate button in create mode");
        form.destroy();

        _t.database.multi_lang = multiLang;
    });

    QUnit.test('char field does not allow html injections', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        await testUtils.fields.editInput(form.$('input[name=foo]'), '<script>throw Error();</script>');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').text(), '<script>throw Error();</script>',
            'the value should have been properly escaped');

        form.destroy();
    });

    QUnit.test('char field trim (or not) characters', async function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo2 = {string: "Foo2", type: "char", trim: false};

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="foo2"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        await testUtils.fields.editInput(form.$('input[name="foo"]'), '  abc  ');
        await testUtils.fields.editInput(form.$('input[name="foo2"]'), '  def  ');

        await testUtils.form.clickSave(form);

        // edit mode
        await testUtils.form.clickEdit(form);

        assert.strictEqual(form.$('input[name="foo"]').val(), 'abc', 'Foo value should have been trimmed');
        assert.strictEqual(form.$('input[name="foo2"]').val(), '  def  ', 'Foo2 value should not have been trimmed');

        form.destroy();
    });

    QUnit.test('input field: change value before pending onchange returns', async function (assert) {
        assert.expect(3);

        this.data.partner.onchanges = {
            product_id: function () {},
        };

        var def;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="product_id"/>' +
                                '<field name="foo"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "onchange") {
                    return Promise.resolve(def).then(function () {
                        return result;
                    });
                } else {
                    return result;
                }
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        assert.strictEqual(form.$('input[name="foo"]').val(), 'My little Foo Value',
            'should contain the default value');

        def = testUtils.makeTestPromise();

        await testUtils.fields.many2one.clickOpenDropdown('product_id');
        await testUtils.fields.many2one.clickHighlightedItem('product_id');

        // set foo before onchange
        await testUtils.fields.editInput(form.$('input[name="foo"]'), "tralala");
        assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            'input should contain tralala');

        // complete the onchange
        def.resolve();
        await testUtils.nextTick();

        assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            'input should contain the same value as before onchange');

        form.destroy();
    });

    QUnit.test('input field: change value before pending onchange renaming', async function (assert) {
        assert.expect(3);

        this.data.partner.onchanges = {
            product_id: function (obj) {
                obj.foo = 'on change value';
            },
        };

        var def = testUtils.makeTestPromise();
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="product_id"/>' +
                        '<field name="foo"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "onchange") {
                    return def.then(function () {
                        return result;
                    });
                } else {
                    return result;
                }
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('input[name="foo"]').val(), 'yop',
            'should contain the correct value');

        await testUtils.fields.many2one.clickOpenDropdown('product_id');
        await testUtils.fields.many2one.clickHighlightedItem('product_id');

        // set foo before onchange
        testUtils.fields.editInput(form.$('input[name="foo"]'), "tralala");
        assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            'input should contain tralala');

        // complete the onchange
        def.resolve();
        assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            'input should contain the same value as before onchange');

        form.destroy();
    });

    QUnit.test('input field: change password value', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="foo" password="True"/>' +
                '</form>',
            res_id: 1,
        });

        assert.notEqual(form.$('.o_field_char').text(), "yop",
            "password field value should not be visible in read mode");
        assert.strictEqual(form.$('.o_field_char').text(), "***",
            "password field value should be hidden with '*' in read mode");

        await testUtils.form.clickEdit(form);

        assert.hasAttrValue(form.$('input.o_field_char'), 'type', 'password',
            "password field input should be with type 'password' in edit mode");
        assert.strictEqual(form.$('input.o_field_char').val(), 'yop',
            "password field input value should be the (non-hidden) password value");

        form.destroy();
    });

    QUnit.test('input field: empty password', async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].foo = false;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="foo" password="True"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_char').text(), "",
            "password field value should be empty in read mode");

        await testUtils.form.clickEdit(form);

        assert.hasAttrValue(form.$('input.o_field_char'), 'type', 'password',
            "password field input should be with type 'password' in edit mode");
        assert.strictEqual(form.$('input.o_field_char').val(), '',
            "password field input value should be the (non-hidden, empty) password value");

        form.destroy();
    });

    QUnit.module('UrlWidget');

    QUnit.test('url widget in form view', async function (assert) {
        assert.expect(9);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="url"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, 'a.o_form_uri.o_field_widget.o_text_overflow',
            "should have a anchor with correct classes");
        assert.hasAttrValue(form.$('a.o_form_uri.o_field_widget.o_text_overflow'), 'href', 'yop',
            "should have proper href link");
        assert.hasAttrValue(form.$('a.o_form_uri.o_field_widget.o_text_overflow'), 'target', '_blank',
            "should have target attribute set to _blank");
        assert.strictEqual(form.$('a.o_form_uri.o_field_widget.o_text_overflow').text(), 'yop',
            "the value should be displayed properly");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, 'input[type="text"].o_field_widget',
            "should have an input for the char field");
        assert.strictEqual(form.$('input[type="text"].o_field_widget').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), 'limbo');

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, 'a.o_form_uri.o_field_widget.o_text_overflow',
            "should still have a anchor with correct classes");
        assert.hasAttrValue(form.$('a.o_form_uri.o_field_widget.o_text_overflow'), 'href', 'limbo',
            "should have proper new href link");
        assert.strictEqual(form.$('a.o_form_uri.o_field_widget.o_text_overflow').text(), 'limbo',
            'the new value should be displayed');

        form.destroy();
    });

    QUnit.test('url widget takes text from proper attribute', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="foo" widget="url" text="kebeclibre"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('a[name="foo"]').text(), 'kebeclibre',
            "url text should come from the text attribute");
        form.destroy();
    });

    QUnit.test('char field in editable list view', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" widget="url"/></tree>',
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').length, 5,
            "should have 5 cells");
        assert.containsN(list, 'a.o_form_uri.o_field_widget.o_text_overflow', 5,
            "should have 5 anchors with correct classes");
        assert.hasAttrValue(list.$('a.o_form_uri.o_field_widget.o_text_overflow').first(), 'href', 'yop',
            "should have proper href link");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yop',
            "value should be displayed properly as text");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(),'o_selected_row', 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        await testUtils.fields.editInput($cell.find('input'), 'brolo');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($cell.parent(), 'o_selected_row', 'should not be in edit mode anymore');
        assert.containsN(list, 'a.o_form_uri.o_field_widget.o_text_overflow', 5,
            "should still have 5 anchors with correct classes");
        assert.hasAttrValue(list.$('a.o_form_uri.o_field_widget.o_text_overflow').first(), 'href', 'brolo',
            "should have proper new href link");
        assert.strictEqual(list.$('a.o_form_uri.o_field_widget.o_text_overflow').first().text(), 'brolo',
            "value should be properly updated");

        list.destroy();
    });

    QUnit.module('CopyClipboard');

    QUnit.test('Char & Text Fields: Copy to clipboard button', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                            '<div>' +
                                '<field name="txt" widget="CopyClipboardText"/>' +
                                '<field name="foo" widget="CopyClipboardChar"/>' +
                            '</div>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.o_clipboard_button.o_btn_text_copy',"Should have copy button on text type field");
        assert.containsOnce(form, '.o_clipboard_button.o_btn_char_copy',"Should have copy button on char type field");

        form.destroy();
    });

    QUnit.test('CopyClipboard widget on unset field', async function (assert) {
        assert.expect(1);

        this.data.partner.records[0].foo = false;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="CopyClipboardChar" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsNone(form, '.o_field_copy[name="foo"] .o_clipboard_button',
            "foo (unset) should not contain a button");

        form.destroy();
    });

    QUnit.test('CopyClipboard widget on readonly unset fields in create mode', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.display_name.readonly = true;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name" widget="CopyClipboardChar" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });

        assert.containsNone(form, '.o_field_copy[name="display_name"] .o_clipboard_button',
            "the readonly unset field should not contain a button");

        form.destroy();
    });

    QUnit.module('FieldText');

    QUnit.test('text fields are correctly rendered', async function (assert) {
        assert.expect(7);

        this.data.partner.fields.foo.type = 'text';
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(form.$('.o_field_text').length, "should have a text area");
        assert.strictEqual(form.$('.o_field_text').text(), 'yop', 'should be "yop" in readonly');

        await testUtils.form.clickEdit(form);

        var $textarea = form.$('textarea.o_field_text');
        assert.ok($textarea.length, "should have a text area");
        assert.strictEqual($textarea.val(), 'yop', 'should still be "yop" in edit');

        testUtils.fields.editInput($textarea, 'hello');
        assert.strictEqual($textarea.val(), 'hello', 'should be "hello" after first edition');

        testUtils.fields.editInput($textarea, 'hello world');
        assert.strictEqual($textarea.val(), 'hello world', 'should be "hello world" after second edition');

        await testUtils.form.clickSave(form);

        assert.strictEqual(form.$('.o_field_text').text(), 'hello world',
            'should be "hello world" after save');
        form.destroy();
    });

    QUnit.test('text fields in edit mode have correct height', async function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.type = 'text';
        this.data.partner.records[0].foo = "f\nu\nc\nk\nm\ni\nl\ng\nr\no\nm";
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        var $field = form.$('.o_field_text');

        assert.strictEqual($field[0].offsetHeight, $field[0].scrollHeight,
            "text field should not have a scroll bar");

        await testUtils.form.clickEdit(form);

        var $textarea = form.$('textarea:first');

        // the difference is to take small calculation errors into account
        assert.strictEqual($textarea[0].clientHeight, $textarea[0].scrollHeight,
            "textarea should not have a scroll bar");
        form.destroy();
    });

    QUnit.test('text fields in edit mode, no vertical resize', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="txt"/>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        var $textarea = form.$('textarea:first');

        assert.strictEqual($textarea.css('resize'), 'none',
            "should not have vertical resize");

        form.destroy();
    });

    QUnit.test('text fields in editable list have correct height', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].txt = "a\nb\nc\nd\ne\nf";

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<list editable="top">' +
                    '<field name="foo"/>' +
                    '<field name="txt"/>' +
                '</list>',
        });

        // Click to enter edit: in this test we specifically do not set
        // the focus on the textarea by clicking on another column.
        // The main goal is to test the resize is actually triggered in this
        // particular case.
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        var $textarea = list.$('textarea:first');

        // make sure the correct data is there
        assert.strictEqual($textarea.val(), this.data.partner.records[0].txt);

        // make sure there is no scroll bar
        assert.strictEqual($textarea[0].clientHeight, $textarea[0].scrollHeight,
            "textarea should not have a scroll bar");

        list.destroy();
    });

    QUnit.test('text fields in edit mode should resize on reset', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.type = 'text';

        this.data.partner.onchanges = {
            bar: function (obj) {
                obj.foo = 'a\nb\nc\nd\ne\nf';
            },
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="bar"/>' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        // edit the form
        // trigger a textarea reset (through onchange) by clicking the box
        // then check there is no scroll bar
        await testUtils.form.clickEdit(form);

        await testUtils.dom.click(form.$('div[name="bar"] input'));

        var $textarea = form.$('textarea:first');
        assert.strictEqual($textarea.innerHeight(), $textarea[0].scrollHeight,
            "textarea should not have a scroll bar");

        form.destroy();
    });

    QUnit.test('text field translatable', async function (assert) {
        assert.expect(3);

        this.data.partner.fields.txt.translate = true;

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="txt"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_button" && args.method === 'translate_fields') {
                    assert.deepEqual(args.args, ["partner",1,"txt"], 'should call "call_button" route');
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.form.clickEdit(form);
        var $button = form.$('textarea + .o_field_translate');
        assert.strictEqual($button.length, 1, "should have a translate button");
        await testUtils.dom.click($button);
        form.destroy();

        form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="txt"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });
        $button = form.$('textarea + .o_field_translate');
        assert.strictEqual($button.length, 0, "should not have a translate button in create mode");
        form.destroy();

        _t.database.multi_lang = multiLang;
    });

    QUnit.test('go to next line (and not the next row) when pressing enter', async function (assert) {
        assert.expect(4);

        this.data.partner.fields.foo.type = 'text';
        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<list editable="top">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                '</list>',
        });

        await testUtils.dom.click(list.$('tbody tr:first .o_list_text'));
        var $textarea = list.$('textarea.o_field_text');
        assert.strictEqual($textarea.length, 1, "should have a text area");
        assert.strictEqual($textarea.val(), 'yop', 'should still be "yop" in edit');

        assert.strictEqual(list.$('textarea').get(0), document.activeElement,
            "text area should have the focus");

        // click on enter
        list.$('textarea')
            .trigger({type: "keydown", which: $.ui.keyCode.ENTER})
            .trigger({type: "keyup", which: $.ui.keyCode.ENTER});

        assert.strictEqual(list.$('textarea').first().get(0), document.activeElement,
            "text area should still have the focus");

        list.destroy();
    });

    // Firefox-specific
    // Copying from <div style="white-space:pre-wrap"> does not keep line breaks
    // See https://bugzilla.mozilla.org/show_bug.cgi?id=1390115
    QUnit.test('copying text fields in RO mode should preserve line breaks', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="txt"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // Copying from a div tag with white-space:pre-wrap doesn't work in Firefox
        assert.strictEqual(form.$('[name="txt"]').prop("tagName").toLowerCase(), 'span',
            "the field contents should be surrounded by a span tag");

        form.destroy();
    });

    QUnit.module('FieldBinary');

    QUnit.test('binary fields are correctly rendered', async function (assert) {
        assert.expect(16);

        // save the session function
        var oldGetFile = session.get_file;
        session.get_file = function (option) {
            assert.strictEqual(option.data.field, 'document',
                "we should download the field document");
            assert.strictEqual(option.data.data, 'coucou==\n',
                "we should download the correct data");
            option.complete();
            return Promise.resolve();
        };

        this.data.partner.records[0].foo = 'coucou.txt';
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="document" filename="foo"/>' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, 'a.o_field_widget[name="document"] > .fa-download',
            "the binary field should be rendered as a downloadable link in readonly");
        assert.strictEqual(form.$('a.o_field_widget[name="document"]').text().trim(), 'coucou.txt',
            "the binary field should display the name of the file in the link");
        assert.strictEqual(form.$('.o_field_char').text(), 'coucou.txt',
            "the filename field should have the file name as value");

        await testUtils.dom.click(form.$('a.o_field_widget[name="document"]'));

        await testUtils.form.clickEdit(form);

        assert.containsNone(form, 'a.o_field_widget[name="document"] > .fa-download',
            "the binary field should not be rendered as a downloadable link in edit");
        assert.strictEqual(form.$('div.o_field_binary_file[name="document"] > input').val(), 'coucou.txt',
            "the binary field should display the file name in the input edit mode");
        assert.hasAttrValue(form.$('.o_field_binary_file > input'), 'readonly', 'readonly',
            "the input should be readonly");
        assert.containsOnce(form, '.o_field_binary_file > .o_clear_file_button',
            "there shoud be a button to clear the file");
        assert.strictEqual(form.$('input.o_field_char').val(), 'coucou.txt',
            "the filename field should have the file name as value");


        await testUtils.dom.click(form.$('.o_field_binary_file > .o_clear_file_button'));

        assert.isNotVisible(form.$('.o_field_binary_file > input'),
            "the input should be hidden");
        assert.strictEqual(form.$('.o_field_binary_file > .o_select_file_button:not(.o_hidden)').length, 1,
            "there shoud be a button to upload the file");
        assert.strictEqual(form.$('input.o_field_char').val(), '',
            "the filename field should be empty since we removed the file");

        await testUtils.form.clickSave(form);
        assert.containsNone(form, 'a.o_field_widget[name="document"] > .fa-download',
            "the binary field should not render as a downloadable link since we removed the file");
        assert.strictEqual(form.$('a.o_field_widget[name="document"]').text().trim(), '',
            "the binary field should not display a filename in the link since we removed the file");
        assert.strictEqual(form.$('.o_field_char').text().trim(), '',
            "the filename field should be empty since we removed the file");

        form.destroy();

        // restore the session function
        session.get_file = oldGetFile;
    });

    QUnit.test('binary fields that are readonly in create mode do not download', async function (assert) {
        assert.expect(2);

        // save the session function
        var oldGetFile = session.get_file;
        session.get_file = function (option) {
            assert.step('We shouldn\'t be getting the file.');
            return oldGetFile.bind(session)(option);
        };

        this.data.partner.onchanges = {
            product_id: function (obj) {
                obj.document = "onchange==\n";
            },
        };

        this.data.partner.fields.document.readonly = true;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="product_id"/>' +
                    '<field name="document" filename="\'yooo\'"/>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickCreate(form);
        await testUtils.fields.many2one.clickOpenDropdown('product_id');
        await testUtils.fields.many2one.clickHighlightedItem('product_id');

        assert.containsOnce(form, 'a.o_field_widget[name="document"] > .fa-download',
            'The link to download the binary should be present');

        testUtils.dom.click(form.$('a.o_field_widget[name="document"]'));

        assert.verifySteps([]); // We shouldn't have passed through steps

        form.destroy();
        session.get_file = oldGetFile;
    });

    QUnit.module('FieldPdfViewer');

    QUnit.test("pdf_viewer without data", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="document" widget="pdf_viewer"/>' +
                '</form>',
        });

        assert.hasClass(form.$('.o_field_widget'), 'o_field_pdfviewer');
        assert.strictEqual(form.$('.o_select_file_button:not(.o_hidden)').length, 1,
            "there should be a visible 'Upload' button");
        assert.isNotVisible(form.$('.o_field_widget iframe.o_pdfview_iframe'),
            "there should be an invisible iframe");
        assert.containsOnce(form, 'input[type="file"]',
            "there should be one input");

        form.destroy();
    });

    QUnit.test("pdf_viewer: basic rendering", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            res_id: 1,
            arch:
                '<form>' +
                    '<field name="document" widget="pdf_viewer"/>' +
                '</form>',
            mockRPC: function (route) {
                if (route.indexOf('/web/static/lib/pdfjs/web/viewer.html') !== -1) {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.hasClass(form.$('.o_field_widget'), 'o_field_pdfviewer');
        assert.strictEqual(form.$('.o_select_file_button:not(.o_hidden)').length, 0,
            "there should not be a any visible 'Upload' button");
        assert.isVisible(form.$('.o_field_widget iframe.o_pdfview_iframe'),
            "there should be an visible iframe");
        assert.hasAttrValue(form.$('.o_field_widget iframe.o_pdfview_iframe'), 'data-src',
            '/web/static/lib/pdfjs/web/viewer.html?file=%2Fweb%2Fcontent%3Fmodel%3Dpartner%26field%3Ddocument%26id%3D1#page=1',
            "the src attribute should be correctly set on the iframe");

        form.destroy();
    });

    QUnit.test("pdf_viewer: upload rendering", async function (assert) {
        assert.expect(6);

        testUtils.mock.patch(field_registry.map.pdf_viewer, {
            on_file_change: function (ev) {
                ev.target = {files: [new Blob()]};
                this._super.apply(this, arguments);
            },
            _getURI: function (fileURI) {
                this._super.apply(this, arguments);
                assert.step('_getURI');
                assert.ok(_.str.startsWith(fileURI, 'blob:'));
                this.PDFViewerApplication = {
                    open: function (URI) {
                        assert.step('open');
                        assert.ok(_.str.startsWith(URI, 'blob:'));
                    },
                };
                return 'about:blank';
            },
        });

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="document" widget="pdf_viewer"/>' +
                '</form>',
        });

        // first upload initialize iframe
        form.$('input[type="file"]').trigger('change');
        assert.verifySteps(['_getURI']);
        // second upload call pdfjs method inside iframe
        form.$('input[type="file"]').trigger('change');
        assert.verifySteps(['open']);

        testUtils.mock.unpatch(field_registry.map.pdf_viewer);
        form.destroy();
    });

    QUnit.test('text field rendering in list view', async function (assert) {
        assert.expect(1);

        var data = {
            foo: {
                fields: {foo: {string: "F", type: "text"}},
                records: [{id: 1, foo: "some text"}]
            },
        };
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('tbody td.o_list_text:contains(some text)').length, 1,
            "should have a td with the .o_list_text class");
        list.destroy();
    });

    QUnit.test("binary fields input value is empty whean clearing after uploading", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                '<field name="document" filename="foo"/>' +
                '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        // // We need to convert the input type since we can't programmatically set the value of a file input
        form.$('.o_input_file').attr('type', 'text').val('coucou.txt');

        assert.strictEqual(form.$('.o_input_file').val(), 'coucou.txt',
            "input value should be changed to \"coucou.txt\"");

        await testUtils.dom.click(form.$('.o_field_binary_file > .o_clear_file_button'));

        assert.strictEqual(form.$('.o_input_file').val(), '',
            "input value should be empty");

        form.destroy();
    });

    QUnit.test('field text in editable list view', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.type = 'text';

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.strictEqual(list.$('textarea').first().get(0), document.activeElement,
            "text area should have the focus");
        list.destroy();
    });

    QUnit.test('field changes are correctly debounced in text fields', async function (assert) {
        var done = assert.async();
        assert.expect(5);

        this.data.partner.fields.foo.type = 'text';

        var def = testUtils.makeTestPromise();
        var nbNotifyChanges = 0;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 2,
            fieldDebounce: 3,
        });

        var _onFieldChanged = form._onFieldChanged;
        form._onFieldChanged = function () {
            _onFieldChanged.apply(form, arguments);
            nbNotifyChanges++;
            def.resolve();
        };

        await testUtils.form.clickEdit(form);

        testUtils.fields.editInput(form.$('textarea').first(), "1");
        assert.strictEqual(nbNotifyChanges, 0,
            "no event should have been triggered");
        testUtils.fields.editInput(form.$('textarea').first(), "12");
        assert.strictEqual(nbNotifyChanges, 0,
            "no event should have been triggered");

        return waitForChangeTriggered().then(async function () {
            assert.strictEqual(nbNotifyChanges, 1,
                "one event should have been triggered");

            // add something in the textarea, then focus another input
            await testUtils.fields.editInput(form.$('textarea').first(), "123");
            assert.strictEqual(nbNotifyChanges, 2,
                "one event should have been triggered immediately");

            return waitForChangeTriggered();
        }).then(function () {
            assert.strictEqual(nbNotifyChanges, 2,
                "no extra event should have been triggered");

            form.destroy();
            done();
        });

        function waitForChangeTriggered() {
            return def.then(function () {
                def = testUtils.makeTestPromise();
                return concurrency.delay(0);
            });
        }
    });

    QUnit.module('FieldImage');

    QUnit.test('image fields are correctly rendered', async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].__last_update = '2017-02-08 10:00:00';
        this.data.partner.records[0].document = 'myimage';

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="document" widget="image" options="{\'size\': [90, 90]}"/> ' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/read') {
                    assert.deepEqual(args.args[1], ['document', '__last_update', 'display_name'], "The fields document, display_name and __last_update should be present when reading an image");
                }
                if (route === 'data:image/png;base64,myimage') {
                    assert.ok(true, "should called the correct route");
                    return Promise.resolve('wow');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.hasClass(form.$('div[name="document"]'),'o_field_image',
            "the widget should have the correct class");
        assert.containsOnce(form, 'div[name="document"] > img',
            "the widget should contain an image");
        assert.hasClass(form.$('div[name="document"] > img'),'img-fluid',
            "the image should have the correct class");
        assert.hasAttrValue(form.$('div[name="document"] > img'), 'width', "90",
            "the image should correctly set its attributes");
        assert.strictEqual(form.$('div[name="document"] > img').css('max-width'), "90px",
            "the image should correctly set its attributes");
        form.destroy();
    });

    QUnit.test('image fields in subviews are loaded correctly', async function (assert) {
        assert.expect(6);

        this.data.partner.records[0].__last_update = '2017-02-08 10:00:00';
        this.data.partner.records[0].document = 'myimage';
        this.data.partner_type.fields.image = {name: 'image', type: 'binary'};
        this.data.partner_type.records[0].image = 'product_image';
        this.data.partner.records[0].timmy = [12];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="document" widget="image" options="{\'size\': [90, 90]}"/>' +
                    '<field name="timmy" widget="many2many">' +
                        '<tree>' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                        '<form>' +
                            '<field name="image" widget="image"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route) {
                if (route === 'data:image/png;base64,myimage') {
                    assert.step("The view's image should have been fetched");
                    return Promise.resolve('wow');
                }
                if (route === 'data:image/png;base64,product_image') {
                    assert.step("The dialog's image should have been fetched");
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.verifySteps(["The view's image should have been fetched"]);

        assert.containsOnce(form, 'tr.o_data_row',
            'There should be one record in the many2many');

        // Actual flow: click on an element of the m2m to get its form view
        await testUtils.dom.click(form.$('tbody td:contains(gold)'));
        assert.strictEqual($('.modal').length, 1,
            'The modal should have opened');
        assert.verifySteps(["The dialog's image should have been fetched"]);

        form.destroy();
    });

    QUnit.test('image fields in x2many list are loaded correctly', async function (assert) {
        assert.expect(2);

        this.data.partner_type.fields.image = {name: 'image', type: 'binary'};
        this.data.partner_type.records[0].image = 'product_image';
        this.data.partner.records[0].timmy = [12];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="timmy" widget="many2many">' +
                        '<tree>' +
                            '<field name="image" widget="image"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route) {
                if (route === 'data:image/png;base64,product_image') {
                    assert.ok(true, "The list's image should have been fetched");
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(form, 'tr.o_data_row',
            'There should be one record in the many2many');

        form.destroy();
    });

    QUnit.test('image fields with required attribute', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="document" required="1" widget="image"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    throw new Error("Should not do a create RPC with unset required image field");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.form.clickSave(form);

        assert.hasClass(form.$('.o_form_view'),'o_form_editable',
            "form view should still be editable");
        assert.hasClass(form.$('.o_field_widget'),'o_field_invalid',
            "image field should be displayed as invalid");

        form.destroy();
    });

    QUnit.module('JournalDashboardGraph', {
        beforeEach: function () {
            _.extend(this.data.partner.fields, {
                graph_data: { string: "Graph Data", type: "text" },
                graph_type: {
                    string: "Graph Type",
                    type: "selection",
                    selection: [['line', 'Line'], ['bar', 'Bar']]
                },
            });
            this.data.partner.records[0].graph_type = "bar";
            this.data.partner.records[1].graph_type = "line";
            var graph_values = [
                {'value': 300, 'label': '5-11 Dec'},
                {'value': 500, 'label': '12-18 Dec'},
                {'value': 100, 'label': '19-25 Dec'},
            ];
            this.data.partner.records[0].graph_data = JSON.stringify([{
                color: 'red',
                title: 'Partner 0',
                values: graph_values,
                key: 'A key',
                area: true,
            }]);
            this.data.partner.records[1].graph_data = JSON.stringify([{
                color: 'blue',
                title: 'Partner 1',
                values: graph_values,
                key: 'A key',
                area: true,
            }]);
        },
    });

    QUnit.test('graph dashboard widget attach/detach callbacks', async function (assert) {
        // This widget is rendered with Chart.js.
        var done = assert.async();
        assert.expect(6);

        testUtils.mock.patch(JournalDashboardGraph, {
            on_attach_callback: function () {
                assert.step('on_attach_callback');
            },
            on_detach_callback: function () {
                assert.step('on_detach_callback');
            },
        });

        createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<field name="graph_type"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                        '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                        '</div>' +
                    '</t>' +
                '</templates></kanban>',
            domain: [['id', 'in', [1, 2]]],
        }).then(function (kanban) {
            assert.verifySteps([
                'on_attach_callback',
                'on_attach_callback'
            ]);

            kanban.on_detach_callback();

            assert.verifySteps([
                'on_detach_callback',
                'on_detach_callback'
            ]);

            kanban.destroy();
            testUtils.mock.unpatch(JournalDashboardGraph);
            done();
        });
    });

    QUnit.test('graph dashboard widget is rendered correctly', async function (assert) {
        var done = assert.async();
        assert.expect(3);

        createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<field name="graph_type"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                        '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                        '</div>' +
                    '</t>' +
                '</templates></kanban>',
            domain: [['id', 'in', [1, 2]]],
        }).then(function (kanban) {
            concurrency.delay(0).then(function () {
                assert.strictEqual(kanban.$('.o_kanban_record:first() .o_graph_barchart').length, 1,
                    "graph of first record should be a barchart");
                assert.strictEqual(kanban.$('.o_kanban_record:nth(1) .o_dashboard_graph').length, 1,
                    "graph of second record should be a linechart");

                // force a re-rendering of the first record (to check if the
                // previous rendered graph is correctly removed from the DOM)
                var firstRecordState = kanban.model.get(kanban.handle).data[0];
                return kanban.renderer.updateRecord(firstRecordState);
            }).then(function () {
                return concurrency.delay(0);
            }).then(function () {
                assert.strictEqual(kanban.$('.o_kanban_record:first() canvas').length, 1,
                    "there should be only one rendered graph by record");

                kanban.destroy();
                done();
            });
        });
    });

    QUnit.test('rendering of a field with dashboard_graph widget in an updated kanban view (ungrouped)', async function (assert) {

        var done = assert.async();
        assert.expect(2);

        createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<field name="graph_type"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                        '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                        '</div>' +
                    '</t>' +
                '</templates></kanban>',
            domain: [['id', 'in', [1, 2]]],
        }).then(function (kanban) {
            concurrency.delay(0).then(function () {
                assert.containsN(kanban, '.o_dashboard_graph canvas', 2, "there should be two graph rendered");
                return kanban.update({});
            }).then(function () {
                return concurrency.delay(0); // one graph is re-rendered
            }).then(function () {
                assert.containsN(kanban, '.o_dashboard_graph canvas', 2, "there should be one graph rendered");
                kanban.destroy();
                done();
            });
        });
    });

    QUnit.test('rendering of a field with dashboard_graph widget in an updated kanban view (grouped)', async function (assert) {

        var done = assert.async();
        assert.expect(2);

        createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<field name="graph_type"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                        '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                        '</div>' +
                    '</t>' +
                '</templates></kanban>',
            domain: [['id', 'in', [1, 2]]],
        }).then(function (kanban) {
            concurrency.delay(0).then(function () {
                assert.containsN(kanban, '.o_dashboard_graph canvas', 2, "there should be two graph rendered");
                return kanban.update({groupBy: ['selection'], domain: [['int_field', '=', 10]]});
            }).then(function () {
                assert.containsOnce(kanban, '.o_dashboard_graph canvas', "there should be one graph rendered");
                kanban.destroy();
                done();
            });
        });
    });

    QUnit.module('AceEditor');

    QUnit.test('ace widget on text fields works', async function (assert) {
        assert.expect(2);
        var done = assert.async();

        this.data.partner.fields.foo.type = 'text';
        testUtils.createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" widget="ace"/>' +
                '</form>',
            res_id: 1,
        }).then(function (form) {
            assert.ok('ace' in window, "the ace library should be loaded");
            assert.ok(form.$('div.ace_content').length, "should have rendered something with ace editor");
            form.destroy();
            done();
        });
    });

    QUnit.module('HandleWidget');

    QUnit.test('handle widget in x2m', async function (assert) {
        assert.expect(6);

        this.data.partner.records[0].p = [2, 4];
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="sequence" widget="handle"/>' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                        '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('td span.o_row_handle').text(), "",
            "handle should not have any content");

        assert.notOk(form.$('td span.o_row_handle').is(':visible'),
            "handle should be invisible in readonly mode");

        assert.containsN(form, 'span.o_row_handle', 2, "should have 2 handles");

        await testUtils.form.clickEdit(form);

        assert.hasClass(form.$('td:first'),'o_handle_cell',
            "column widget should be displayed in css class");

        assert.ok(form.$('td span.o_row_handle').is(':visible'),
            "handle should be visible in readonly mode");

        testUtils.dom.click(form.$('td').eq(1));
        assert.containsOnce(form, 'td:first span.o_row_handle',
            "content of the cell should have been replaced");
        form.destroy();
    });

    QUnit.test('handle widget with falsy values', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree>' +
                    '<field name="sequence" widget="handle"/>' +
                    '<field name="display_name"/>' +
                '</tree>',
        });

        assert.containsN(list, '.o_row_handle:visible', this.data.partner.records.length,
            'there should be a visible handle for each record');
        list.destroy();
    });


    QUnit.module('FieldDate');

    QUnit.test('date field: toggle datepicker [REQUIRE FOCUS]', async function (assert) {
        assert.expect(3);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form><field name="foo"/><field name="date"/></form>',
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
            },
        });

        assert.strictEqual($('.bootstrap-datetimepicker-widget:visible').length, 0,
            "datepicker should be closed initially");

        await testUtils.dom.openDatepicker(form.$('.o_datepicker'));

        assert.strictEqual($('.bootstrap-datetimepicker-widget:visible').length, 1,
            "datepicker should be opened");

        // focus another field
        await testUtils.dom.click(form.$('.o_field_widget[name=foo]').focus().mouseenter());

        assert.strictEqual($('.bootstrap-datetimepicker-widget:visible').length, 0,
            "datepicker should close itself when the user clicks outside");

        form.destroy();
    });

    QUnit.test('date field is empty if no date is set', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 4,
        });
        var $span = form.$('span.o_field_widget');
        assert.strictEqual($span.length, 1, "should have one span in the form view");
        assert.strictEqual($span.text(), "", "and it should be empty");
        form.destroy();
    });

    QUnit.test('date field should remove the date  if the date is not valid', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 4,
        });
        // switch to edit mode
        await testUtils.form.clickEdit(form);
        // set an invalid date
        var $input = form.$('.o_field_widget[name=date] input');
        $input.val('mmmh').trigger('change');
        assert.strictEqual($input.text(), "", "The date field should be empty");
        form.destroy();
    });

    QUnit.test('date field value should not set on first click', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 4,
        });

        await testUtils.form.clickEdit(form);

        // open datepicker and select a date
        testUtils.dom.openDatepicker(form.$('.o_datepicker'));
        assert.strictEqual(form.$('.o_datepicker_input').val(), '', "date field's input should be empty on first click");
        testUtils.dom.click($('.day:contains(22)'));

        // re-open datepicker
        testUtils.dom.openDatepicker(form.$('.o_datepicker'));
        assert.strictEqual($('.day.active').text(), '22',
            "datepicker should be highlight with 22nd day of month");

        form.destroy();
    });

    QUnit.test('date field in form view (with positive time zone offset)', async function (assert) {
        assert.expect(8);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    assert.strictEqual(args.args[1].date, '2017-02-22', 'the correct value should be saved');
                }
                return this._super.apply(this, arguments);
            },
            translateParameters: {  // Avoid issues due to localization formats
              date_format: '%m/%d/%Y',
            },
            session: {
                getTZOffset: function () {
                    return 120; // Should be ignored by date fields
                },
            },
        });

        assert.strictEqual(form.$('.o_field_date').text(), '02/03/2017',
            'the date should be correctly displayed in readonly');

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        // open datepicker and select another value
        testUtils.dom.openDatepicker(form.$('.o_datepicker'));
        assert.ok($('.bootstrap-datetimepicker-widget').length, 'datepicker should be open');
        assert.strictEqual($('.day.active').data('day'), '02/03/2017', 'datepicker should be highlight February 3');
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch').first());
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch:eq(1)').first());
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .year:contains(2017)'));
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .month').eq(1));
        testUtils.dom.click($('.day:contains(22)'));
        assert.ok(!$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/22/2017',
            'the selected date should be displayed in the input');

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_date').text(), '02/22/2017',
            'the selected date should be displayed after saving');
        form.destroy();
    });

    QUnit.test('date field in form view (with negative time zone offset)', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            translateParameters: {  // Avoid issues due to localization formats
              date_format: '%m/%d/%Y',
            },
            session: {
                getTZOffset: function () {
                    return -120; // Should be ignored by date fields
                },
            },
        });

        assert.strictEqual(form.$('.o_field_date').text(), '02/03/2017',
            'the date should be correctly displayed in readonly');

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        form.destroy();
    });

    QUnit.test('date field dropdown disappears on scroll', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<div class="scrollable" style="height: 2000px;">' +
                        '<field name="date"/>' +
                    '</div>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        await testUtils.dom.openDatepicker(form.$('.o_datepicker'));
        
        assert.containsOnce($('body'), '.bootstrap-datetimepicker-widget', "datepicker should be opened");

        form.el.dispatchEvent(new Event('scroll'));
        assert.containsNone($('body'), '.bootstrap-datetimepicker-widget', "datepicker should be closed");

        form.destroy();
    });

    QUnit.test('date field with warn_future option', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="date" options="{\'datepicker\': {\'warn_future\': true}}"/>' +
                 '</form>',
            res_id: 4,
        });

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        // open datepicker and select another value
        testUtils.dom.openDatepicker(form.$('.o_datepicker'));
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch').first());
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch:eq(1)'));
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .year').eq(11));
        testUtils.dom.click($('.bootstrap-datetimepicker-widget .month').eq(11));
        testUtils.dom.click($('.day:contains(31)'));

        var $warn = form.$('.o_datepicker_warning:visible');
        assert.strictEqual($warn.length, 1, "should have a warning in the form view");

        testUtils.fields.editSelect(form.$('.o_field_widget[name=date] input'), '');  // remove the value

        $warn = form.$('.o_datepicker_warning:visible');
        assert.strictEqual($warn.length, 0, "the warning in the form view should be hidden");

        form.destroy();
    });

    QUnit.test('date field with warn_future option: do not overwrite datepicker option', async function (assert) {
        assert.expect(2);

        // Making sure we don't have a legit default value
        // or any onchange that would set the value
        this.data.partner.fields.date.default = undefined;
        this.data.partner.onchanges = {};

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="foo" />' + // Do not let the date field get the focus in the first place
                    '<field name="date" options="{\'datepicker\': {\'warn_future\': true}}"/>' +
                 '</form>',
            res_id: 1,
        });

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('input[name="date"]').val(), '02/03/2017',
        'The existing record should have a value for the date field');

        // save with no changes
        await testUtils.form.clickSave(form);

        //Create a new record
        await testUtils.form.clickCreate(form);

        assert.notOk(form.$('input[name="date"]').val(),
            'The new record should not have a value that the framework would have set');

        form.destroy();
    });

    QUnit.test('date field in editable list view', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="date"/>' +
                  '</tree>',
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
            },
            session: {
                getTZOffset: function () {
                    return 0;
                },
            },
        });

        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        assert.strictEqual($cell.text(), '02/03/2017',
            'the date should be displayed correctly in readonly');
        await testUtils.dom.click($cell);

        assert.containsOnce(list, 'input.o_datepicker_input',
            "the view should have a date input for editable mode");

        assert.strictEqual(list.$('input.o_datepicker_input').get(0), document.activeElement,
            "date input should have the focus");

        assert.strictEqual(list.$('input.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        // open datepicker and select another value
        await testUtils.dom.openDatepicker(list.$('.o_datepicker'));
        assert.ok($('.bootstrap-datetimepicker-widget').length, 'datepicker should be open');
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch').first());
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch:eq(1)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .year:contains(2017)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .month').eq(1));
        await testUtils.dom.click($('.day:contains(22)'));
        assert.ok(!$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');
        assert.strictEqual(list.$('.o_datepicker_input').val(), '02/22/2017',
            'the selected date should be displayed in the input');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('tr.o_data_row td:not(.o_list_record_selector)').text(), '02/22/2017',
            'the selected date should be displayed after saving');

        list.destroy();
    });

    QUnit.test('date field remove value', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    assert.strictEqual(args.args[1].date, false, 'the correct value should be saved');
                }
                return this._super.apply(this, arguments);
            },
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
            },
        });

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        testUtils.fields.editAndTrigger(form.$('.o_datepicker_input'), '', ['input', 'change', 'focusout']);
        assert.strictEqual(form.$('.o_datepicker_input').val(), '',
            'should have correctly removed the value');

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_date').text(), '',
            'the selected date should be displayed after saving');

        form.destroy();
    });

    QUnit.test('do not trigger a field_changed for datetime field with date widget', async function (assert) {
        assert.expect(3);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="datetime" widget="date"/></form>',
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M:%S',
            },
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/08/2017',
            'the date should be correct');

        testUtils.fields.editAndTrigger(form.$('input[name="datetime"]'),'02/08/2017', ['input', 'change', 'focusout']);
        await testUtils.form.clickSave(form);

        assert.verifySteps(['read']); // should not have save as nothing changed

        form.destroy();
    });

    QUnit.test('field date should select its content onclick when there is one', async function (assert) {
        assert.expect(2);
        var done = assert.async();

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="date"/></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$el.on({
            'show.datetimepicker': function () {
                assert.ok($('.bootstrap-datetimepicker-widget').is(':visible'),
                    'bootstrap-datetimepicker is visible');
                assert.strictEqual(window.getSelection().toString(), "02/03/2017",
                    'The whole input of the date field should have been selected');
                done();
            }
        });

        testUtils.dom.openDatepicker(form.$('.o_datepicker'));

        form.destroy();
    });

    QUnit.test('date field support internalization', async function (assert) {
        assert.expect(2);

        var originalLocale = moment.locale();
        var originalParameters = _.clone(core._t.database.parameters);

        _.extend(core._t.database.parameters, {date_format: '%d. %b %Y', time_format: '%H:%M:%S'});
        moment.defineLocale('norvegianForTest', {
            monthsShort: 'jan._feb._mars_april_mai_juni_juli_aug._sep._okt._nov._des.'.split('_'),
            monthsParseExact: true,
            dayOfMonthOrdinalParse: /\d{1,2}\./,
            ordinal: '%d.',
        });

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 1,
        });

        var dateViewForm = form.$('.o_field_date').text();
        await testUtils.dom.click(form.$buttons.find('.o_form_button_edit'));
        await testUtils.openDatepicker(form.$('.o_datepicker'));
        assert.strictEqual(form.$('.o_datepicker_input').val(), dateViewForm,
            "input date field should be the same as it was in the view form");

        await testUtils.dom.click($('.day:contains(30)'));
        var dateEditForm = form.$('.o_datepicker_input').val();
        await testUtils.dom.click(form.$buttons.find('.o_form_button_save'));
        assert.strictEqual(form.$('.o_field_date').text(), dateEditForm,
            "date field should be the same as the one selected in the view form");

        moment.locale(originalLocale);
        moment.updateLocale('norvegianForTest', null);
        core._t.database.parameters = originalParameters;

        form.destroy();
    });

    QUnit.module('FieldDatetime');

    QUnit.test('datetime field in form view', async function (assert) {
        assert.expect(7);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="datetime"/></form>',
            res_id: 1,
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M:%S',
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        var expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
        assert.strictEqual(form.$('.o_field_date').text(), expectedDateString,
            'the datetime should be correctly displayed in readonly');

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_datepicker_input').val(), expectedDateString,
            'the datetime should be correct in edit mode');

        // datepicker should not open on focus
        assert.containsNone($('body'), '.bootstrap-datetimepicker-widget');

        testUtils.dom.openDatepicker(form.$('.o_datepicker'));
        assert.containsOnce($('body'), '.bootstrap-datetimepicker-widget');

        // select 22 February at 8:23:33
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch').first());
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch:eq(1)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .year:contains(2017)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .month').eq(3));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .day:contains(22)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .fa-clock-o'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .hour:contains(08)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-minute'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .minute:contains(25)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-second'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .second:contains(35)'));
        assert.ok(!$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');

        var newExpectedDateString = "04/22/2017 08:25:35";
        assert.strictEqual(form.$('.o_datepicker_input').val(), newExpectedDateString,
            'the selected date should be displayed in the input');

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_date').text(), newExpectedDateString,
            'the selected date should be displayed after saving');

        form.destroy();
    });


    QUnit.test('datetime field not visible in form view should not capture the focus on keyboard navigation', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="txt"/>' +
            '<field name="datetime" invisible="True"/></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$el.find('textarea[name=txt]').trigger($.Event('keydown', {
            which: $.ui.keyCode.TAB,
            keyCode: $.ui.keyCode.TAB,
        }));
        assert.strictEqual(document.activeElement, form.$buttons.find('.o_form_button_save')[0],
            "the save button should be selected, because the datepicker did not capture the focus");
        form.destroy();
    });

    QUnit.test('datetime field with datetime formatted without second', async function (assert) {
        assert.expect(2);

        this.data.partner.fields.datetime.default = "2017-08-02 12:00:05";
        this.data.partner.fields.datetime.required = true;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="datetime"/></form>',
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M',
            },
        });

        var expectedDateString = "08/02/2017 12:00"; // 10:00:00 without timezone
        assert.strictEqual(form.$('.o_field_date input').val(), expectedDateString,
            'the datetime should be correctly displayed in readonly');

        await testUtils.form.clickDiscard(form);

        assert.strictEqual($('.modal').length, 0,
            "there should not be a Warning dialog");

        form.destroy();
    });

    QUnit.test('datetime field in editable list view', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="datetime"/>' +
                  '</tree>',
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M:%S',
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        var expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        assert.strictEqual($cell.text(), expectedDateString,
            'the datetime should be correctly displayed in readonly');

        // switch to edit mode
        await testUtils.dom.click($cell);
        assert.containsOnce(list, 'input.o_datepicker_input',
            "the view should have a date input for editable mode");

        assert.strictEqual(list.$('input.o_datepicker_input').get(0), document.activeElement,
            "date input should have the focus");

        assert.strictEqual(list.$('input.o_datepicker_input').val(), expectedDateString,
            'the date should be correct in edit mode');

        assert.containsNone($('body'), '.bootstrap-datetimepicker-widget');
        testUtils.dom.openDatepicker(list.$('.o_datepicker'));
        assert.containsOnce($('body'), '.bootstrap-datetimepicker-widget');

        // select 22 February at 8:23:33
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch').first());
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch:eq(1)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .year:contains(2017)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .month').eq(3));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .day:contains(22)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .fa-clock-o'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .hour:contains(08)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-minute'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .minute:contains(25)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-second'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .second:contains(35)'));
        assert.ok(!$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');

        var newExpectedDateString = "04/22/2017 08:25:35";
        assert.strictEqual(list.$('.o_datepicker_input').val(), newExpectedDateString,
            'the selected datetime should be displayed in the input');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('tr.o_data_row td:not(.o_list_record_selector)').text(), newExpectedDateString,
            'the selected datetime should be displayed after saving');

        list.destroy();
    });

    QUnit.test('datetime field remove value', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="datetime"/></form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    assert.strictEqual(args.args[1].datetime, false, 'the correct value should be saved');
                }
                return this._super.apply(this, arguments);
            },
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M:%S',
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/08/2017 12:00:00',
            'the date time should be correct in edit mode');

        await testUtils.fields.editAndTrigger($('.o_datepicker_input'), '', ['input', 'change', 'focusout']);
        assert.strictEqual(form.$('.o_datepicker_input').val(), '',
            "should have an empty input");

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_date').text(), '',
            'the selected date should be displayed after saving');

        form.destroy();
    });

    QUnit.test('datetime field with date/datetime widget (with day change)', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].datetime = "2017-02-08 02:00:00"; // UTC

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="datetime"/>' +
                        '</tree>' +
                        '<form>' +
                            '<field name="datetime" widget="date"/>' +
                        '</form>' +
                     '</field>' +
                 '</form>',
            res_id: 1,
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M:%S',
            },
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
        });

        var expectedDateString = "02/07/2017 22:00:00"; // local time zone
        assert.strictEqual(form.$('.o_field_widget[name=p] .o_data_cell').text(), expectedDateString,
            'the datetime (datetime widget) should be correctly displayed in tree view');

        // switch to form view
        await testUtils.dom.click(form.$('.o_field_widget[name=p] .o_data_row'));
        assert.strictEqual($('.modal .o_field_date[name=datetime]').text(), '02/07/2017',
            'the datetime (date widget) should be correctly displayed in form view');

        form.destroy();
    });

    QUnit.test('datetime field with date/datetime widget (without day change)', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].datetime = "2017-02-08 10:00:00"; // without timezone

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="datetime"/>' +
                        '</tree>' +
                        '<form>' +
                            '<field name="datetime" widget="date"/>' +
                        '</form>' +
                     '</field>' +
                 '</form>',
            res_id: 1,
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M:%S',
            },
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
        });

        var expectedDateString = "02/08/2017 06:00:00"; // with timezone
        assert.strictEqual(form.$('.o_field_widget[name=p] .o_data_cell').text(), expectedDateString,
            'the datetime (datetime widget) should be correctly displayed in tree view');

        // switch to form view
        await testUtils.dom.click(form.$('.o_field_widget[name=p] .o_data_row'));
        assert.strictEqual($('.modal .o_field_date[name=datetime]').text(), '02/08/2017',
            'the datetime (date widget) should be correctly displayed in form view');

        form.destroy();
    });

    QUnit.test('datepicker option: daysOfWeekDisabled', async function (assert) {
        assert.expect(42);

        this.data.partner.fields.datetime.default = "2017-08-02 12:00:05";
        this.data.partner.fields.datetime.required = true;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="datetime" ' +
                            'options=\'{"datepicker": {"daysOfWeekDisabled": [0, 6]}}\'/>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickCreate(form);
        testUtils.dom.openDatepicker(form.$('.o_datepicker'));
        $.each($('.day:last-child(),.day:nth-child(2)'), function (index, value) {
            assert.hasClass(value, 'disabled', 'first and last days must be disabled');
        });
        // the assertions below could be replaced by a single hasClass classic on the jQuery set using the idea
        // All not <=> not Exists. But we want to be sure that the set is non empty. We don't have an helper
        // function for that.
        $.each($('.day:not(:last-child()):not(:nth-child(2))'), function (index, value) {
            assert.doesNotHaveClass(value, 'disabled', 'other days must stay clickable');
        });
        form.destroy();
    });

    QUnit.module('FieldMonetary');

    QUnit.test('monetary field in form view', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="monetary"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '$\u00a09.10',
            'The value should be displayed properly.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '9.10',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').parent().children().first().text(), '$',
            'The input should be preceded by a span containing the currency symbol.');

        await testUtils.fields.editInput(form.$('.o_field_monetary input'), '108.2458938598598');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '108.2458938598598',
            'The value should not be formated yet.');

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '$\u00a0108.25',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('monetary field rounding using formula in form view', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="monetary"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        // Test computation and rounding
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('.o_field_monetary input'), '=100/3');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '$\u00a033.33',
            'The new value should be calculated and rounded properly.');

        form.destroy();
    });

    QUnit.test('monetary field with currency symbol after', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="monetary"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '0.00\u00a0€',
            'The value should be displayed properly.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '0.00',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').parent().children().eq(1).text(), '€',
            'The input should be followed by a span containing the currency symbol.');

        await testUtils.fields.editInput(form.$('.o_field_widget[name=qux] input'), '108.2458938598598');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '108.2458938598598',
            'The value should not be formated yet.');

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '108.25\u00a0€',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('monetary field with currency digits != 2', async function (assert) {
        assert.expect(5);

        this.data.partner.records = [{
            id: 1,
            bar: false,
            foo: "pouet",
            int_field: 68,
            qux: 99.1234,
            currency_id: 1,
        }];
        this.data.currency.records = [{
            id: 1,
            display_name: "VEF",
            symbol: "Bs.F",
            position: "after",
            digits: [16, 4],
        }];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="monetary"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '99.1234\u00a0Bs.F',
            'The value should be displayed properly.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '99.1234',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').parent().children().eq(1).text(), 'Bs.F',
            'The input should be followed by a span containing the currency symbol.');

        await testUtils.fields.editInput(form.$('.o_field_widget[name=qux] input'), '99.111111111');
        assert.strictEqual(form.$('.o_field_widget[name=qux] input').val(), '99.111111111',
            'The value should not be formated yet.');

        await testUtils.form.clickSave(form);
        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_field_widget').first().text(), '99.1111\u00a0Bs.F',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('monetary field in editable list view', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="qux" widget="monetary"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                  '</tree>',
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        var dollarValues = list.$('td').filter(function () {return _.str.include($(this).text(), '$');});
        assert.strictEqual(dollarValues.length, 1,
            'Only one line has dollar as a currency.');

        var euroValues = list.$('td').filter(function () {return _.str.include($(this).text(), '€');});
        assert.strictEqual(euroValues.length, 1,
            'One one line has euro as a currency.');

        var zeroValues = list.$('td.o_data_cell').filter(function () {return $(this).text() === '';});
        assert.strictEqual(zeroValues.length, 1,
            'Unset float values should be rendered as empty strings.');

        // switch to edit mode
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector):contains($)');
        await testUtils.dom.click($cell);

        assert.strictEqual($cell.children().length, 1,
            'The cell td should only contain the special div of monetary widget.');
        assert.containsOnce(list, '[name="qux"] input',
            'The view should have 1 input for editable monetary float.');
        assert.strictEqual(list.$('[name="qux"] input').val(), '9.10',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(list.$('[name="qux"] input').parent().children().first().text(), '$',
            'The input should be preceded by a span containing the currency symbol.');

        await testUtils.fields.editInput(list.$('[name="qux"] input'), '108.2458938598598');
        assert.strictEqual(list.$('[name="qux"] input').val(), '108.2458938598598',
            'The typed value should be correctly displayed.');

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('tr.o_data_row td:not(.o_list_record_selector):contains($)').text(), '$\u00a0108.25',
            'The new value should be rounded properly.');

        list.destroy();
    });

    QUnit.test('monetary field with real monetary field in model', async function (assert) {
        assert.expect(7);

        this.data.partner.fields.qux.type = "monetary";
        this.data.partner.fields.quux = {
            string: "Quux", type: "monetary", digits: [16,1], searchable: true, readonly: true,
        };

        (_.find(this.data.partner.records, function (record) { return record.id === 5; })).quux = 4.2;

        this.data.partner.onchanges = {
            bar: function (obj) {
                obj.qux = obj.bar ? 100 : obj.qux;
            },
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux"/>' +
                        '<field name="quux"/>' +
                        '<field name="currency_id"/>' +
                        '<field name="bar"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        assert.strictEqual(form.$('.o_field_monetary').first().html(), "$&nbsp;9.10",
            "readonly value should contain the currency");
        assert.strictEqual(form.$('.o_field_monetary').first().next().html(), "$&nbsp;4.20",
            "readonly value should contain the currency");

        await testUtils.form.clickEdit(form);

        assert.strictEqual(form.$('.o_field_monetary > input').val(), "9.10",
            "input value in edition should only contain the value, without the currency");

        await testUtils.dom.click(form.$('input[type="checkbox"]'));
        assert.containsOnce(form, '.o_field_monetary > input',
            "After the onchange, the monetary <input/> should not have been duplicated");
        assert.containsOnce(form, '.o_field_monetary[name=quux]',
            "After the onchange, the monetary readonly field should not have been duplicated");

        await testUtils.fields.many2one.clickOpenDropdown('currency_id');
        await testUtils.fields.many2one.clickItem('currency_id','€');
        assert.strictEqual(form.$('.o_field_monetary > span').html(), "€",
            "After currency change, the monetary field currency should have been updated");
        assert.strictEqual(form.$('.o_field_monetary').first().next().html(), "4.20&nbsp;€",
            "readonly value should contain the updated currency");

        form.destroy();
    });

    QUnit.test('monetary field with monetary field given in options', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.qux.type = "monetary";
        this.data.partner.fields.company_currency_id = {
            string: "Company Currency", type: "many2one", relation: "currency",
        };
        this.data.partner.records[4].company_currency_id = 2;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" options="{\'currency_field\': \'company_currency_id\'}"/>' +
                        '<field name="company_currency_id"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        assert.strictEqual(form.$('.o_field_monetary').html(), "9.10&nbsp;€",
            "field monetary should be formatted with correct currency");

        form.destroy();
    });

    QUnit.test('should keep the focus when being edited in x2many lists', async function (assert) {
        assert.expect(6);

        this.data.partner.fields.currency_id.default = 1;
        this.data.partner.fields.m2m = {
            string: "m2m", type: "many2many", relation: 'partner', default: [[6, false, [2]]],
        };
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p"/>' +
                        '<field name="m2m"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,list': '<tree editable="bottom">' +
                    '<field name="qux" widget="monetary"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                '</tree>',
            },
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        // test the monetary field inside the one2many
        var $o2m = form.$('.o_field_widget[name=p]');
        await testUtils.dom.click($o2m.find('.o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput($o2m.find('.o_field_widget input'), "22");

        assert.strictEqual($o2m.find('.o_field_widget input').get(0), document.activeElement,
            "the focus should still be on the input");
        assert.strictEqual($o2m.find('.o_field_widget input').val(), "22",
            "the value should not have been formatted yet");

        await testUtils.dom.click(form.$el);

        assert.strictEqual($o2m.find('.o_field_widget[name=qux]').html(), "$&nbsp;22.00",
            "the value should have been formatted after losing the focus");

        // test the monetary field inside the many2many
        var $m2m = form.$('.o_field_widget[name=m2m]');
        await testUtils.dom.click($m2m.find('.o_data_row td:first'));
        await testUtils.fields.editInput($m2m.find('.o_field_widget input'), "22");

        assert.strictEqual($m2m.find('.o_field_widget input').get(0), document.activeElement,
            "the focus should still be on the input");
        assert.strictEqual($m2m.find('.o_field_widget input').val(), "22",
            "the value should not have been formatted yet");

        await testUtils.dom.click(form.$el);

        assert.strictEqual($m2m.find('.o_field_widget[name=qux]').html(), "22.00&nbsp;€",
            "the value should have been formatted after losing the focus");

        form.destroy();
    });

    QUnit.test('monetary field with currency set by an onchange',async function (assert) {
        // this test ensures that the monetary field can be re-rendered with and
        // without currency (which can happen as the currency can be set by an
        // onchange)
        assert.expect(8);

        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.currency_id = obj.int_field ? 2 : null;
            },
        };

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="int_field"/>' +
                        '<field name="qux" widget="monetary"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</tree>',
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.containsOnce(list, 'div.o_field_widget[name=qux] input',
            "monetary field should have been rendered correctly (without currency)");
        assert.containsNone(list, '.o_field_widget[name=qux] span',
            "monetary field should have been rendered correctly (without currency)");

        // set a value for int_field -> should set the currency and re-render qux
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'),'7');
        assert.containsOnce(list, 'div.o_field_widget[name=qux] input',
            "monetary field should have been re-rendered correctly (with currency)");
        assert.strictEqual(list.$('.o_field_widget[name=qux] span:contains(€)').length, 1,
            "monetary field should have been re-rendered correctly (with currency)");
        var $quxInput = list.$('.o_field_widget[name=qux] input');
        await testUtils.dom.click($quxInput);
        assert.strictEqual(document.activeElement, $quxInput[0],
            "focus should be on the qux field's input");

        // unset the value of int_field -> should unset the currency and re-render qux
        await testUtils.dom.click(list.$('.o_field_widget[name=int_field]'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'),'0');
        $quxInput = list.$('div.o_field_widget[name=qux] input');
        assert.strictEqual($quxInput.length, 1,
            "monetary field should have been re-rendered correctly (without currency)");
        assert.containsNone(list, '.o_field_widget[name=qux] span',
            "monetary field should have been re-rendered correctly (without currency)");
        await testUtils.dom.click($quxInput);
        assert.strictEqual(document.activeElement, $quxInput[0],
            "focus should be on the qux field's input");

        list.destroy();
    });

    QUnit.module('FieldInteger');

    QUnit.test('integer field when unset', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="int_field"/></form>',
            res_id: 4,
        });

        assert.doesNotHaveClass(form.$('.o_field_widget'), 'o_field_empty',
            'Non-set integer field should be recognized as 0.');
        assert.strictEqual(form.$('.o_field_widget').text(), "0",
            'Non-set integer field should be recognized as 0.');

        form.destroy();
    });

    QUnit.test('integer field in form view', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="int_field"/></form>',
            res_id: 2,
        });

        assert.doesNotHaveClass(form.$('.o_field_widget'), 'o_field_empty',
            'Integer field should be considered set for value 0.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('input[name=int_field]').val(), '0',
            'The value should be rendered correctly in edit mode.');

        await testUtils.fields.editInput(form.$('input[name=int_field]'), '-18');
        assert.strictEqual(form.$('input[name=int_field]').val(), '-18',
            'The value should be correctly displayed in the input.');

        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').text(), '-18',
            'The new value should be saved and displayed properly.');

        form.destroy();
    });

    QUnit.test('integer field rounding using formula in form view', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="int_field"/></form>',
            res_id: 2,
        });

        // Test computation and rounding
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('input[name=int_field]'), '=100/3');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '33',
            'The new value should be calculated properly.');

        form.destroy();
    });

    QUnit.test('integer field in form view with virtual id', async function (assert) {
        assert.expect(1);
        var params = {
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="id"/></form>',
        };

        params.res_id = this.data.partner.records[1].id = "2-20170808020000";
        var form = await createView(params);
        assert.strictEqual(form.$('.o_field_widget').text(), "2-20170808020000",
            "Should display virtual id");

        form.destroy();
    });

    QUnit.test('integer field in editable list view', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field"/>' +
                  '</tree>',
        });

        var zeroValues = list.$('td').filter(function () {return $(this).text() === '0';});
        assert.strictEqual(zeroValues.length, 1,
            'Unset integer values should not be rendered as zeros.');

        // switch to edit mode
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);

        assert.containsOnce(list, 'input[name="int_field"]',
            'The view should have 1 input for editable integer.');

        await testUtils.fields.editInput(list.$('input[name="int_field"]'), '-28');
        assert.strictEqual(list.$('input[name="int_field"]').val(), '-28',
            'The value should be displayed properly in the input.');

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('td:not(.o_list_record_selector)').first().text(), '-28',
            'The new value should be saved and displayed properly.');

        list.destroy();
    });

    QUnit.test('integer field with type number option', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                '<field name="int_field" options="{\'type\': \'number\'}"/>' +
            '</form>',
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.ok(form.$('.o_field_widget')[0].hasAttribute('type'),
            'Integer field with option type must have a type attribute.');
        assert.hasAttrValue(form.$('.o_field_widget'), 'type', 'number',
            'Integer field with option type must have a type attribute equals to "number".');

        await testUtils.fields.editInput(form.$('input[name=int_field]'), '1234567890');
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget').val(), '1234567890',
            'Integer value must be not formatted if input type is number.');
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').text(), '1,234,567,890',
            'Integer value must be formatted in readonly view even if the input type is number.');

        form.destroy();
    });

    QUnit.test('integer field without type number option', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                '<field name="int_field"/>' +
            '</form>',
            res_id: 4,
            translateParameters: {
                thousands_sep: ",",
                grouping: [3, 0],
            },
        });

        await testUtils.form.clickEdit(form);
        assert.hasAttrValue(form.$('.o_field_widget'), 'type', 'text',
            'Integer field without option type must have a text type (default type).');

        await testUtils.fields.editInput(form.$('input[name=int_field]'), '1234567890');
        await testUtils.form.clickSave(form);
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget').val(), '1,234,567,890',
            'Integer value must be formatted if input type isn\'t number.');

        form.destroy();
    });


    QUnit.module('FieldFloatTime');

    QUnit.test('float_time field in form view', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="float_time"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    // 48 / 60 = 0.8
                    assert.strictEqual(args.args[1].qux, -11.8, 'the correct float value should be saved');
                }
                return this._super.apply(this, arguments);
            },
            res_id: 5,
        });

        // 9 + 0.1 * 60 = 9.06
        assert.strictEqual(form.$('.o_field_widget').first().text(), '09:06',
            'The formatted time value should be displayed properly.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('input[name=qux]').val(), '09:06',
            'The value should be rendered correctly in the input.');

        await testUtils.fields.editInput(form.$('input[name=qux]'), '-11:48');
        assert.strictEqual(form.$('input[name=qux]').val(), '-11:48',
            'The new value should be displayed properly in the input.');

        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '-11:48',
            'The new value should be saved and displayed properly.');

        form.destroy();
    });


    QUnit.module('FieldFloatFactor');

    QUnit.test('float_factor field in form view', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="float_factor" options="{\'factor\': 0.5}" digits="[16,2]"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    // 16.4 / 2 = 8.2
                    assert.strictEqual(args.args[1].qux, 4.6, 'the correct float value should be saved');
                }
                return this._super.apply(this, arguments);
            },
            res_id: 5,
        });
        assert.strictEqual(form.$('.o_field_widget').first().text(), '4.55', // 9.1 / 0.5
            'The formatted value should be displayed properly.');

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('input[name=qux]').val(), '4.55',
            'The value should be rendered correctly in the input.');

        await testUtils.fields.editInput(form.$('input[name=qux]'), '2.3');

        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').first().text(), '2.30',
            'The new value should be saved and displayed properly.');

        form.destroy();
    });

    QUnit.module('FieldFloatToggle');

    QUnit.test('float_toggle field in form view', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="float_toggle" options="{\'factor\': 0.125, \'range\': [0, 1, 0.75, 0.5, 0.25]}" digits="[5,3]"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    // 1.000 / 0.125 = 8
                    assert.strictEqual(args.args[1].qux, 8, 'the correct float value should be saved');
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });
        assert.strictEqual(form.$('.o_field_widget').first().text(), '0.056',
            'The formatted time value should be displayed properly.');

        await testUtils.form.clickEdit(form);

        assert.strictEqual(form.$('button.o_field_float_toggle').text(), '0.056',
            'The value should be rendered correctly on the button.');

        await testUtils.dom.click(form.$('button.o_field_float_toggle'));

        assert.strictEqual(form.$('button.o_field_float_toggle').text(), '1.000',
            'The value should be rendered correctly on the button.');

        await testUtils.form.clickSave(form);

        assert.strictEqual(form.$('.o_field_widget').first().text(), '1.000',
            'The new value should be saved and displayed properly.');

        form.destroy();
    });


    QUnit.module('PhoneWidget');

    QUnit.test('phone field in form view on normal screens', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="phone"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            config: {
                device: {
                    size_class: config.device.SIZES.LG,
                },
            },
        });

        var $phone = form.$('a.o_field_widget.o_form_uri');
        assert.strictEqual($phone.length, 1,
            "should have rendered the phone number as a link with correct classes");
        assert.strictEqual($phone.text(), 'yop',
            "value should be displayed properly");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, 'input[type="text"].o_field_widget',
            "should have an input for the phone field");
        assert.strictEqual(form.$('input[type="text"].o_field_widget').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        await testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), 'new');

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('a.o_field_widget.o_form_uri').text(), 'new',
            "new value should be displayed properly");

        form.destroy();
    });

    QUnit.test('phone field in editable list view on normal screens', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
            config: {
                device: {
                    size_class: config.device.SIZES.LG,
                },
            },
        });

        assert.containsN(list, 'tbody td:not(.o_list_record_selector)', 5);
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yop',
            "value should be displayed properly");

        assert.containsN(list, 'a.o_field_widget.o_form_uri', 5,
            "should have the correct classnames");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(),'o_selected_row', 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        await testUtils.fields.editInput($cell.find('input'), 'new');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($cell.parent(), 'o_selected_row', 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'new',
            "value should be properly updated");
        assert.containsN(list, 'a.o_field_widget.o_form_uri', 5,
            "should still have links with correct classes");

        list.destroy();
    });

    QUnit.test('use TAB to navigate to a phone field', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                            '<field name="foo" widget="phone"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });

        testUtils.dom.click(form.$('input[name=display_name]'));
        assert.strictEqual(form.$('input[name="display_name"]')[0], document.activeElement,
            "display_name should be focused");
        form.$('input[name="display_name"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$('input[name="foo"]')[0], document.activeElement,
            "foo should be focused");

        form.destroy();
    });

    QUnit.module('PriorityWidget');

    QUnit.test('priority widget when not set', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="selection" widget="priority"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_field_widget.o_priority:not(.o_field_empty)').length, 1,
            "widget should be considered set, even though there is no value for this field");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 0,
            "should have no full star since there is no value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 2,
            "should have two empty stars since there is no value");

        form.destroy();
    });

    QUnit.test('priority widget in form view', async function (assert) {
        assert.expect(22);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="selection" widget="priority"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget.o_priority:not(.o_field_empty)').length, 1,
            "widget should be considered set");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should have one empty star since the value is the second value");

        // hover last star
        form.$('.o_field_widget.o_priority a.o_priority_star.fa-star-o').last().trigger('mouseover');
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 2,
            "should temporary have two full stars since we are hovering the third value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 0,
            "should temporary have no empty star since we are hovering the third value");

        // Here we should test with mouseout, but currently the effect associated with it
        // occurs in a setTimeout after 200ms so it's not trivial to test it here.

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should still have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should still have one empty star since the value is the second value");

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should still have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should still have one empty star since the value is the second value");

        // switch to edit mode to check that the new value was properly written
        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should still have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should still have one empty star since the value is the second value");

        // click on the second star in edit mode
        await testUtils.dom.click(form.$('.o_field_widget.o_priority a.o_priority_star.fa-star-o').last());

        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(form.$('.o_field_widget.o_priority').find('a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        form.destroy();
    });

    QUnit.test('priority widget in editable list view', async function (assert) {
        assert.expect(25);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="selection" widget="priority"/></tree>',
        });

        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority:not(.o_field_empty)').length, 1,
            "widget should be considered set");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 1,
            "should have one full star since the value is the second value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 1,
            "should have one empty star since the value is the second value");

        // Here we should test with mouseout, but currently the effect associated with it
        // occurs in a setTimeout after 200ms so it's not trivial to test it here.

        // switch to edit mode and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 1,
            "should have one full star since the value is the second value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 1,
            "should have one empty star since the value is the second value");

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 1,
            "should have one full star since the value is the second value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 1,
            "should have one empty star since the value is the second value");

        // hover last star
        list.$('.o_data_row .o_priority a.o_priority_star.fa-star-o').first().trigger('mouseenter');
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('a.o_priority_star.fa-star').length, 2,
            "should temporary have two full stars since we are hovering the third value");
        assert.strictEqual(list.$('.o_data_row').first().find('a.o_priority_star.fa-star-o').length, 0,
            "should temporary have no empty star since we are hovering the third value");

        // click on the first star in readonly mode
        await testUtils.dom.click(list.$('.o_priority a.o_priority_star.fa-star').first());

        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 0,
            "should now have no full star since the value is the first value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 2,
            "should now have two empty stars since the value is the first value");

        // re-enter edit mode to force re-rendering the widget to check if the value was correctly saved
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);

        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 0,
            "should now only have no full star since the value is the first value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 2,
            "should now have two empty stars since the value is the first value");

        // Click on second star in edit mode
        await testUtils.dom.click(list.$('.o_priority a.o_priority_star.fa-star-o').last());

        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        list.destroy();
    });


    QUnit.module('StateSelection Widget');

    QUnit.test('state_selection widget in form view', async function (assert) {
        assert.expect(21);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="selection" widget="state_selection"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                disable_autofocus: true,
            },
        });

        assert.containsOnce(form, '.o_field_widget.o_selection > a span.o_status.o_status_red',
            "should have one red status since selection is the second, blocked state");
        assert.containsNone(form, '.o_field_widget.o_selection > a span.o_status.o_status_green',
            "should not have one green status since selection is the second, blocked state");
        assert.containsNone(form, '.dropdown-menu.state:visible',
            "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await testUtils.dom.click(form.$('.o_field_widget.o_selection .o_status').first());
        assert.containsOnce(form, '.dropdown-menu.state:visible',
            "there should be a dropdown");
        assert.containsN(form, '.dropdown-menu.state:visible .dropdown-item', 2,
            "there should be two options in the dropdown");

        // Click on the first option, "Normal"
        await testUtils.dom.click(form.$('.dropdown-menu.state:visible .dropdown-item').first());
        assert.containsNone(form, '.dropdown-menu.state:visible',
            "there should not be a dropdown anymore");
        assert.containsNone(form, '.o_field_widget.o_selection > a span.o_status.o_status_red',
            "should not have one red status since selection is the first, normal state");
        assert.containsNone(form, '.o_field_widget.o_selection > a span.o_status.o_status_green',
            "should not have one green status since selection is the first, normal state");
        assert.containsOnce(form, '.o_field_widget.o_selection > a span.o_status',
            "should have one grey status since selection is the first, normal state");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsNone(form, '.dropdown-menu.state:visible',
            "there should still not be a dropdown");
        assert.containsNone(form, '.o_field_widget.o_selection > a span.o_status.o_status_red',
            "should still not have one red status since selection is the first, normal state");
        assert.containsNone(form, '.o_field_widget.o_selection > a span.o_status.o_status_green',
            "should still not have one green status since selection is the first, normal state");
        assert.containsOnce(form, '.o_field_widget.o_selection > a span.o_status',
            "should still have one grey status since selection is the first, normal state");

        // Click on the status button to make the dropdown appear
        await testUtils.dom.click(form.$('.o_field_widget.o_selection .o_status').first());
        assert.containsOnce(form, '.dropdown-menu.state:visible',
            "there should be a dropdown");
        assert.containsN(form, '.dropdown-menu.state:visible .dropdown-item', 2,
            "there should be two options in the dropdown");

        // Click on the last option, "Done"
        await testUtils.dom.click(form.$('.dropdown-menu.state:visible .dropdown-item').last());
        assert.containsNone(form, '.dropdown-menu.state:visible',
            "there should not be a dropdown anymore");
        assert.containsNone(form, '.o_field_widget.o_selection > a span.o_status.o_status_red',
            "should not have one red status since selection is the third, done state");
        assert.containsOnce(form, '.o_field_widget.o_selection > a span.o_status.o_status_green',
            "should have one green status since selection is the third, done state");

        // save
        await testUtils.form.clickSave(form);
        assert.containsNone(form, '.dropdown-menu.state:visible',
            "there should still not be a dropdown anymore");
        assert.containsNone(form, '.o_field_widget.o_selection > a span.o_status.o_status_red',
            "should still not have one red status since selection is the third, done state");
        assert.containsOnce(form, '.o_field_widget.o_selection > a span.o_status.o_status_green',
            "should still have one green status since selection is the third, done state");

        form.destroy();
    });

    QUnit.test('state_selection widget with readonly modifier', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="selection" widget="state_selection" readonly="1"/></form>',
            res_id: 1,
        });

        assert.hasClass(form.$('.o_selection'), 'o_readonly_modifier');
        assert.hasClass(form.$('.o_selection > a'), 'disabled');
        assert.isNotVisible(form.$('.dropdown-menu.state'));

        await testUtils.dom.click(form.$('.o_selection > a'));
        assert.isNotVisible(form.$('.dropdown-menu.state'));

        form.destroy();
    });

    QUnit.test('state_selection widget in editable list view', async function (assert) {
        assert.expect(32);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="selection" widget="state_selection"/>' +
                  '</tree>',
        });

        assert.containsN(list, '.o_state_selection_cell .o_selection > a span.o_status', 5,
            "should have five status selection widgets");
        assert.containsOnce(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_red',
            "should have one red status");
        assert.containsOnce(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_green',
            "should have one green status");
        assert.containsNone(list, '.dropdown-menu.state:visible',
            "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        var $cell = list.$('tbody td.o_state_selection_cell').first();
        await testUtils.dom.click(list.$('.o_state_selection_cell .o_selection > a span.o_status').first());
        assert.doesNotHaveClass($cell.parent(), 'o_selected_row',
            'should not be in edit mode since we clicked on the state selection widget');
        assert.containsOnce(list, '.dropdown-menu.state:visible',
            "there should be a dropdown");
        assert.containsN(list, '.dropdown-menu.state:visible .dropdown-item', 2,
            "there should be two options in the dropdown");

        // Click on the first option, "Normal"
        await testUtils.dom.click(list.$('.dropdown-menu.state:visible .dropdown-item').first());
        assert.containsN(list, '.o_state_selection_cell .o_selection > a span.o_status', 5,
            "should still have five status selection widgets");
        assert.containsNone(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_red',
            "should now have no red status");
        assert.containsOnce(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_green',
            "should still have one green status");
        assert.containsNone(list, '.dropdown-menu.state:visible',
            "there should not be a dropdown");

        // switch to edit mode and check the result
        $cell = list.$('tbody td.o_state_selection_cell').first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(),'o_selected_row',
            'should now be in edit mode');
        assert.containsN(list, '.o_state_selection_cell .o_selection > a span.o_status', 5,
            "should still have five status selection widgets");
        assert.containsNone(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_red',
            "should now have no red status");
        assert.containsOnce(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_green',
            "should still have one green status");
        assert.containsNone(list, '.dropdown-menu.state:visible',
            "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await testUtils.dom.click(list.$('.o_state_selection_cell .o_selection > a span.o_status').first());
        assert.containsOnce(list, '.dropdown-menu.state:visible',
            "there should be a dropdown");
        assert.containsN(list, '.dropdown-menu.state:visible .dropdown-item', 2,
            "there should be two options in the dropdown");

        // Click on another row
        var $lastCell = list.$('tbody td.o_state_selection_cell').last();
        await testUtils.dom.click($lastCell);
        assert.containsNone(list, '.dropdown-menu.state:visible',
            "there should not be a dropdown anymore");
        var $firstCell = list.$('tbody td.o_state_selection_cell').first();
        assert.doesNotHaveClass($firstCell.parent(), 'o_selected_row',
            'first row should not be in edit mode anymore');
        assert.hasClass($lastCell.parent(),'o_selected_row',
            'last row should be in edit mode');

        // Click on the last status button to make the dropdown appear
        await testUtils.dom.click(list.$('.o_state_selection_cell .o_selection > a span.o_status').last());
        assert.containsOnce(list, '.dropdown-menu.state:visible',
            "there should be a dropdown");
        assert.containsN(list, '.dropdown-menu.state:visible .dropdown-item', 2,
            "there should be two options in the dropdown");

        // Click on the last option, "Done"
        await testUtils.dom.click(list.$('.dropdown-menu.state:visible .dropdown-item').last());
        assert.containsNone(list, '.dropdown-menu.state:visible',
            "there should not be a dropdown anymore");
        assert.containsN(list, '.o_state_selection_cell .o_selection > a span.o_status', 5,
            "should still have five status selection widgets");
        assert.containsNone(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_red',
            "should still have no red status");
        assert.containsN(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_green', 2,
            "should now have two green status");
        assert.containsNone(list, '.dropdown-menu.state:visible',
            "there should not be a dropdown");

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.containsN(list, '.o_state_selection_cell .o_selection > a span.o_status', 5,
            "should have five status selection widgets");
        assert.containsNone(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_red',
            "should have no red status");
        assert.containsN(list, '.o_state_selection_cell .o_selection > a span.o_status.o_status_green', 2,
            "should have two green status");
        assert.containsNone(list, '.dropdown-menu.state:visible',
            "there should not be a dropdown");

        list.destroy();
    });


    QUnit.module('FavoriteWidget');

    QUnit.test('favorite widget in kanban view', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<templates>' +
                        '<t t-name="kanban-box">' +
                            '<div>' +
                                '<field name="bar" widget="boolean_favorite" />' +
                            '</div>' +
                        '</t>' +
                    '</templates>' +
                  '</kanban>',
            domain: [['id', '=', 1]],
        });

        assert.containsOnce(kanban, '.o_kanban_record .o_field_widget.o_favorite > a i.fa.fa-star',
            'should be favorite');
        assert.strictEqual(kanban.$('.o_kanban_record .o_field_widget.o_favorite > a').text(), ' Remove from Favorites',
            'the label should say "Remove from Favorites"');

        // click on favorite
        await testUtils.dom.click(kanban.$('.o_field_widget.o_favorite'));
        assert.containsNone(kanban, '.o_kanban_record  .o_field_widget.o_favorite > a i.fa.fa-star',
            'should not be favorite');
        assert.strictEqual(kanban.$('.o_kanban_record  .o_field_widget.o_favorite > a').text(), ' Add to Favorites',
            'the label should say "Add to Favorites"');

        kanban.destroy();
    });

    QUnit.test('favorite widget in form view', async function (assert) {
        assert.expect(10);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="bar" widget="boolean_favorite" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.o_field_widget.o_favorite > a i.fa.fa-star',
            'should be favorite');
        assert.strictEqual(form.$('.o_field_widget.o_favorite > a').text(), ' Remove from Favorites',
            'the label should say "Remove from Favorites"');

        // click on favorite
        await testUtils.dom.click(form.$('.o_field_widget.o_favorite'));
        assert.containsNone(form, '.o_field_widget.o_favorite > a i.fa.fa-star',
            'should not be favorite');
        assert.strictEqual(form.$('.o_field_widget.o_favorite > a').text(), ' Add to Favorites',
            'the label should say "Add to Favorites"');

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.o_field_widget.o_favorite > a i.fa.fa-star-o',
            'should not be favorite');
        assert.strictEqual(form.$('.o_field_widget.o_favorite > a').text(), ' Add to Favorites',
            'the label should say "Add to Favorites"');

        // click on favorite
        await testUtils.dom.click(form.$('.o_field_widget.o_favorite'));
        assert.containsOnce(form, '.o_field_widget.o_favorite > a i.fa.fa-star',
            'should be favorite');
        assert.strictEqual(form.$('.o_field_widget.o_favorite > a').text(), ' Remove from Favorites',
            'the label should say "Remove from Favorites"');

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.o_field_widget.o_favorite > a i.fa.fa-star',
            'should be favorite');
        assert.strictEqual(form.$('.o_field_widget.o_favorite > a').text(), ' Remove from Favorites',
            'the label should say "Remove from Favorites"');

        form.destroy();
    });

    QUnit.test('favorite widget in editable list view without label', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="bar" widget="boolean_favorite" nolabel="1" />' +
                  '</tree>',
        });

        assert.containsOnce(list, '.o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star',
            'should be favorite');

        // switch to edit mode
        await testUtils.dom.click(list.$('tbody td:not(.o_list_record_selector)').first());
        assert.containsOnce(list, '.o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star',
            'should be favorite');

        // click on favorite
        await testUtils.dom.click(list.$('.o_data_row:first .o_field_widget.o_favorite'));
        assert.containsNone(list, '.o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star',
            'should not be favorite');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.containsOnce(list, '.o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star-o',
            'should not be favorite');

        list.destroy();
    });


    QUnit.module('LabelSelectionWidget');

    QUnit.test('label_selection widget in form view', async function (assert) {
        assert.expect(12);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="selection" widget="label_selection" ' +
                            ' options="{\'classes\': {\'normal\': \'secondary\', \'blocked\': \'warning\',\'done\': \'success\'}}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.o_field_widget.badge.badge-warning',
            "should have a warning status label since selection is the second, blocked state");
        assert.containsNone(form, '.o_field_widget.badge.badge-secondary',
            "should not have a default status since selection is the second, blocked state");
        assert.containsNone(form, '.o_field_widget.badge.badge-success',
            "should not have a success status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_field_widget.badge.badge-warning').text(), 'Blocked',
            "the label should say 'Blocked' since this is the label value for that state");

        // // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.o_field_widget.badge.badge-warning',
            "should have a warning status label since selection is the second, blocked state");
        assert.containsNone(form, '.o_field_widget.badge.badge-secondary',
            "should not have a default status since selection is the second, blocked state");
        assert.containsNone(form, '.o_field_widget.badge.badge-success',
            "should not have a success status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_field_widget.badge.badge-warning').text(), 'Blocked',
            "the label should say 'Blocked' since this is the label value for that state");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.o_field_widget.badge.badge-warning',
            "should have a warning status label since selection is the second, blocked state");
        assert.containsNone(form, '.o_field_widget.badge.badge-secondary',
            "should not have a default status since selection is the second, blocked state");
        assert.containsNone(form, '.o_field_widget.badge.badge-success',
            "should not have a success status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_field_widget.badge.badge-warning').text(), 'Blocked',
            "the label should say 'Blocked' since this is the label value for that state");

        form.destroy();
    });

    QUnit.test('label_selection widget in editable list view', async function (assert) {
        assert.expect(21);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="selection" widget="label_selection"' +
                    ' options="{\'classes\': {\'normal\': \'secondary\', \'blocked\': \'warning\',\'done\': \'success\'}}"/>' +
                  '</tree>',
        });

        assert.strictEqual(list.$('.o_field_widget.badge:not(:empty)').length, 3,
            "should have three visible status labels");
        assert.containsOnce(list, '.o_field_widget.badge.badge-warning',
            "should have one warning status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-warning').text(), 'Blocked',
            "the warning label should read 'Blocked'");
        assert.containsOnce(list, '.o_field_widget.badge.badge-secondary',
            "should have one default status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-secondary').text(), 'Normal',
            "the default label should read 'Normal'");
        assert.containsOnce(list, '.o_field_widget.badge.badge-success',
            "should have one success status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-success').text(), 'Done',
            "the success label should read 'Done'");

        // switch to edit mode and check the result
        await testUtils.dom.clickFirst(list.$('tbody td:not(.o_list_record_selector)'));
        assert.strictEqual(list.$('.o_field_widget.badge:not(:empty)').length, 3,
            "should have three visible status labels");
        assert.containsOnce(list, '.o_field_widget.badge.badge-warning',
            "should have one warning status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-warning').text(), 'Blocked',
            "the warning label should read 'Blocked'");
        assert.containsOnce(list, '.o_field_widget.badge.badge-secondary',
            "should have one default status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-secondary').text(), 'Normal',
            "the default label should read 'Normal'");
        assert.containsOnce(list, '.o_field_widget.badge.badge-success',
            "should have one success status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-success').text(), 'Done',
            "the success label should read 'Done'");

        // save and check the result
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.strictEqual(list.$('.o_field_widget.badge:not(:empty)').length, 3,
            "should have three visible status labels");
        assert.containsOnce(list, '.o_field_widget.badge.badge-warning',
            "should have one warning status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-warning').text(), 'Blocked',
            "the warning label should read 'Blocked'");
        assert.containsOnce(list, '.o_field_widget.badge.badge-secondary',
            "should have one default status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-secondary').text(), 'Normal',
            "the default label should read 'Normal'");
        assert.containsOnce(list, '.o_field_widget.badge.badge-success',
            "should have one success status label");
        assert.strictEqual(list.$('.o_field_widget.badge.badge-success').text(), 'Done',
            "the success label should read 'Done'");

        list.destroy();
    });


    QUnit.module('StatInfo');

    QUnit.test('statinfo widget formats decimal precision', async function (assert) {
        // sometimes the round method can return numbers such as 14.000001
        // when asked to round a number to 2 decimals, as such is the behaviour of floats.
        // we check that even in that eventuality, only two decimals are displayed
        assert.expect(2);

        this.data.partner.fields.monetary = {string: "Monetary", type: 'monetary'};
        this.data.partner.records[0].monetary = 9.999999;
        this.data.partner.records[0].currency_id = 1;

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<button class="oe_stat_button" name="items" icon="fa-gear">' +
                            '<field name="qux" widget="statinfo"/>' +
                        '</button>' +
                        '<button class="oe_stat_button" name="money" icon="fa-money">' +
                            '<field name="monetary" widget="statinfo"/>' +
                        '</button>' +
                  '</form>',
            res_id: 1,
        });

        // formatFloat renders according to this.field.digits
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').eq(0).text(),
            '0.4', "Default precision should be [16,1]");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').eq(1).text(),
            '10.00', "Currency decimal precision should be 2");

        form.destroy();
    });

    QUnit.test('statinfo widget in form view', async function (assert) {
        assert.expect(9);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<button class="oe_stat_button" name="items"  type="object" icon="fa-gear">' +
                                '<field name="int_field" widget="statinfo"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            'int_field', "should have 'int_field' as text");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should still have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should still have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            'int_field', "should have 'int_field' as text");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            'int_field', "should have 'int_field' as text");

        form.destroy();
    });

    QUnit.test('statinfo widget in form view with specific label_field', async function (assert) {
        assert.expect(9);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<button class="oe_stat_button" name="items"  type="object" icon="fa-gear">' +
                                '<field string="Useful stat button" name="int_field" widget="statinfo" ' +
                                        'options="{\'label_field\': \'foo\'}"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="foo" invisible="1"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            'yop', "should have 'yop' as text, since it is the value of field foo");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should still have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should still have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            'yop', "should have 'yop' as text, since it is the value of field foo");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            'yop', "should have 'yop' as text, since it is the value of field foo");

        form.destroy();
    });

    QUnit.test('statinfo widget in form view with no label', async function (assert) {
        assert.expect(9);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<button class="oe_stat_button" name="items"  type="object" icon="fa-gear">' +
                                '<field string="Useful stat button" name="int_field" widget="statinfo" nolabel="1"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="foo" invisible="1"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            '', "should not have any label");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should still have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should still have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            '', "should not have any label");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.oe_stat_button .o_field_widget.o_stat_info',
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_field_widget.o_stat_info .o_stat_text').text(),
            '', "should not have any label");

        form.destroy();
    });


    QUnit.module('PercentPie');

    QUnit.test('percentpie widget in form view with value < 50%', async function (assert) {
        assert.expect(12);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="int_field" widget="percentpie"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.containsOnce(form, '.o_field_percent_pie.o_field_widget .o_pie',
            "should have a pie chart");
        assert.strictEqual(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_pie_value').text(),
            '10%', "should have 10% as pie value since int_field=10");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').first().attr('style'),
            'transform: rotate(180deg);'), "left mask should be covering the whole left side of the pie");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').last().attr('style'),
            'transform: rotate(36deg);'), "right mask should be rotated from 360*(10/100) = 36 degrees");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.o_field_percent_pie.o_field_widget .o_pie',
            "should have a pie chart");
        assert.strictEqual(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_pie_value').text(),
            '10%', "should have 10% as pie value since int_field=10");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').first().attr('style'),
            'transform: rotate(180deg);'), "left mask should be covering the whole left side of the pie");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').last().attr('style'),
            'transform: rotate(36deg);'), "right mask should be rotated from 360*(10/100) = 36 degrees");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.o_field_percent_pie.o_field_widget .o_pie',
            "should have a pie chart");
        assert.strictEqual(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_pie_value').text(),
            '10%', "should have 10% as pie value since int_field=10");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').first().attr('style'),
            'transform: rotate(180deg);'), "left mask should be covering the whole left side of the pie");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').last().attr('style'),
            'transform: rotate(36deg);'), "right mask should be rotated from 360*(10/100) = 36 degrees");

        form.destroy();
    });

    QUnit.test('percentpie widget in form view with value > 50%', async function (assert) {
        assert.expect(12);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="int_field" widget="percentpie"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 3,
        });

        assert.containsOnce(form, '.o_field_percent_pie.o_field_widget .o_pie',
            "should have a pie chart");
        assert.strictEqual(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_pie_value').text(),
            '80%', "should have 80% as pie value since int_field=80");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').first().attr('style'),
            'transform: rotate(288deg);'), "left mask should be rotated from 360*(80/100) = 288 degrees");
        assert.hasClass(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').last(),'o_full',
            "right mask should be hidden since the value > 50%");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, '.o_field_percent_pie.o_field_widget .o_pie',
            "should have a pie chart");
        assert.strictEqual(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_pie_value').text(),
            '80%', "should have 80% as pie value since int_field=80");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').first().attr('style'),
            'transform: rotate(288deg);'), "left mask should be rotated from 360*(80/100) = 288 degrees");
        assert.hasClass(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').last(),'o_full',
            "right mask should be hidden since the value > 50%");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.o_field_percent_pie.o_field_widget .o_pie',
            "should have a pie chart");
        assert.strictEqual(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_pie_value').text(),
            '80%', "should have 80% as pie value since int_field=80");
        assert.ok(_.str.include(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').first().attr('style'),
            'transform: rotate(288deg);'), "left mask should be rotated from 360*(80/100) = 288 degrees");
        assert.hasClass(form.$('.o_field_percent_pie.o_field_widget .o_pie .o_mask').last(),'o_full',
            "right mask should be hidden since the value > 50%");

        form.destroy();
    });

    // TODO: This test would pass without any issue since all the classes and
    //       custom style attributes are correctly set on the widget in list
    //       view, but since the scss itself for this widget currently only
    //       applies inside the form view, the widget is unusable. This test can
    //       be uncommented when we refactor the scss files so that this widget
    //       stylesheet applies in both form and list view.
    // QUnit.test('percentpie widget in editable list view', async function(assert) {
    //     assert.expect(10);
    //
    //     var list = await createView({
    //         View: ListView,
    //         model: 'partner',
    //         data: this.data,
    //         arch: '<tree editable="bottom">' +
    //                 '<field name="foo"/>' +
    //                 '<field name="int_field" widget="percentpie"/>' +
    //               '</tree>',
    //     });
    //
    //     assert.containsN(list, '.o_field_percent_pie .o_pie', 5,
    //         "should have five pie charts");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole left side of the pie");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // switch to edit mode and check the result
//    testUtils.dom.click(     list.$('tbody td:not(.o_list_record_selector)').first());
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // save
//    testUtils.dom.click(     list.$buttons.find('.o_list_button_save'));
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     list.destroy();
    // });


    QUnit.module('FieldDomain');

    QUnit.test('The domain editor should not crash the view when given a dynamic filter', async function (assert) {
        //dynamic filters (containing variables, such as uid, parent or today)
        //are not handled by the domain editor, but it shouldn't crash the view
        assert.expect(1);

        this.data.partner.records[0].foo = '[["int_field", "=", uid]]';

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="foo" widget="domain" options="{\'model\': \'partner\'}"/>' +
                    '<field name="int_field" invisible="1"/>' +
                '</form>',
            res_id: 1,
            session: {
                user_context: {uid: 14},
            },
        });

        assert.strictEqual(form.$('.o_read_mode').text(), "This domain is not supported.",
            "The widget should not crash the view, but gracefully admit its failure.");
        form.destroy();
    });

    QUnit.test('basic domain field usage is ok', async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].foo = "[]";

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="domain" options="{\'model\': \'partner_type\'}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        await testUtils.form.clickEdit(form);

        // As the domain is empty, there should be a button to add the first
        // domain part
        var $domain = form.$(".o_field_domain");
        var $domainAddFirstNodeButton = $domain.find(".o_domain_add_first_node_button");
        assert.equal($domainAddFirstNodeButton.length, 1,
            "there should be a button to create first domain element");

        // Clicking on the button should add the [["id", "=", "1"]] domain, so
        // there should be a field selector in the DOM
        await testUtils.dom.click($domainAddFirstNodeButton);
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1,
            "there should be a field selector");

        // Focusing the field selector input should open the field selector
        // popover
        await testUtils.dom.triggerEvents($fieldSelector, ['focusin']);
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

        assert.containsOnce($fieldSelectorPopover, '.o_field_selector_search input',
            "field selector popover should contain a search input");

        // The popover should contain the list of partner_type fields and so
        // there should be the "Color index" field
        var $lis = $fieldSelectorPopover.find("li");
        var $colorIndex = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Color index") >= 0) {
                $colorIndex = $li;
            }
        });
        assert.equal($colorIndex.length, 1,
            "field selector popover should contain 'Color index' field");

        // Clicking on this field should close the popover, then changing the
        // associated value should reveal one matched record
        await testUtils.dom.click($colorIndex);
        await testUtils.fields.editAndTrigger($('.o_domain_leaf_value_input'), 2, ['change']);
        assert.equal($domain.find(".o_domain_show_selection_button").text().trim().substr(0, 2), "1 ",
            "changing color value to 2 should reveal only one record");

        // Saving the form view should show a readonly domain containing the
        // "color" field
        await testUtils.form.clickSave(form);
        $domain = form.$(".o_field_domain");
        assert.ok($domain.html().indexOf("Color index") >= 0,
            "field selector readonly value should now contain 'Color index'");
        form.destroy();
    });

    QUnit.test('domain field is correctly reset on every view change', async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].foo = '[["id","=",1]]';
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="bar"/>' +
                            '<field name="foo" widget="domain" options="{\'model\': \'bar\'}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        await testUtils.form.clickEdit(form);

        // As the domain is equal to [["id", "=", 1]] there should be a field
        // selector to change this
        var $domain = form.$(".o_field_domain");
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1,
            "there should be a field selector");

        // Focusing its input should open the field selector popover
        await testUtils.dom.triggerEvents($fieldSelector, ['focusin']);
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

        // As the value of the "bar" field is "product", the field selector
        // popover should contain the list of "product" fields
        var $lis = $fieldSelectorPopover.find("li");
        var $sampleLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Product Name") >= 0) {
                $sampleLi = $li;
            }
        });
        assert.strictEqual($lis.length, 1,
            "field selector popover should contain only one field");
        assert.strictEqual($sampleLi.length, 1,
            "field selector popover should contain 'Product Name' field");

        // Now change the value of the "bar" field to "partner_type"
        await testUtils.dom.click(form.$("input.o_field_widget"));
        await testUtils.fields.editInput(form.$("input.o_field_widget"), "partner_type");

        // Refocusing the field selector input should open the popover again
        $fieldSelector = form.$(".o_field_selector");
        $fieldSelector.trigger('focusin');
        $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

        // Now the list of fields should be the ones of the "partner_type" model
        $lis = $fieldSelectorPopover.find("li");
        $sampleLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Color index") >= 0) {
                $sampleLi = $li;
            }
        });
        assert.strictEqual($lis.length, 2,
            "field selector popover should contain two fields");
        assert.strictEqual($sampleLi.length, 1,
            "field selector popover should contain 'Color index' field");
        form.destroy();
    });

    QUnit.test('domain field can be reset with a new domain (from onchange)', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].foo = '[]';
        this.data.partner.onchanges = {
            display_name: function (obj) {
                obj.foo = '[["id", "=", 1]]';
            },
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="foo" widget="domain" options="{\'model\': \'partner\'}"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.equal(form.$('.o_domain_show_selection_button').text().trim(), '5 record(s)',
            "the domain being empty, there should be 5 records");

        // update display_name to trigger the onchange and reset foo
        await testUtils.fields.editInput(form.$('.o_field_widget[name=display_name]'), 'new value');

        assert.equal(form.$('.o_domain_show_selection_button').text().trim(), '1 record(s)',
            "the domain has changed, there should be only 1 record");

        form.destroy();
    });

    QUnit.test('domain field: handle false domain as []', async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].foo = false;
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="bar"/>' +
                            '<field name="foo" widget="domain" options="{\'model\': \'bar\'}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_count') {
                    assert.deepEqual(args.args[0], [], "should send a valid domain");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget[name=foo]:not(.o_field_empty)').length, 1,
            "there should be a domain field, not considered empty");

        await testUtils.form.clickEdit(form);

        var $warning = form.$('.o_field_widget[name=foo] .text-warning');
        assert.strictEqual($warning.length, 0, "should not display that the domain is invalid");

        form.destroy();
    });

    QUnit.test('basic domain field: show the selection', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].foo = "[]";

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="domain" options="{\'model\': \'partner_type\'}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner_type,false,list': '<tree><field name="display_name"/></tree>',
                'partner_type,false,search': '<search><field name="name" string="Name"/></search>',
            },
            res_id: 1,
        });

        assert.equal(form.$(".o_domain_show_selection_button").text().trim().substr(0, 2), "2 ",
            "selection should contain 2 records");

        // open the selection
        await testUtils.dom.click(form.$(".o_domain_show_selection_button"));
        assert.strictEqual($('.modal .o_list_view .o_data_row').length, 2,
            "should have open a list view with 2 records in a dialog");

        // click on a record -> should not open the record
        // we don't actually check that it doesn't open the record because even
        // if it tries to, it will crash as we don't define an arch in this test
        await testUtils.dom.click($('.modal .o_list_view .o_data_row:first .o_data_cell'));

        form.destroy();
    });

    QUnit.module('FieldProgressBar');

    QUnit.test('Field ProgressBar: max_value should update', async function (assert) {
        assert.expect(2);

        this.data.partner.records = this.data.partner.records.slice(0,1);
        this.data.partner.records[0].qux = 2;

        this.data.partner.onchanges = {
            display_name: function (obj) {
                obj.int_field = 999;
                obj.qux = 5;
            }
        };

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="display_name" />' +
                    '<field name="qux" invisible="1" />' +
                    '<field name="int_field" widget="progressbar" options="{\'current_value\': \'int_field\', \'max_value\': \'qux\'}" />' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_progressbar_value').text(), '10 / 2',
            'The initial value of the progress bar should be correct');

        // trigger the onchange
        await testUtils.fields.editInput(form.$('.o_input[name=display_name]'), 'new name');

        assert.strictEqual(form.$('.o_progressbar_value').text(), '999 / 5',
            'The value of the progress bar should be correct after the update');

        form.destroy();
    });
});
});
});
