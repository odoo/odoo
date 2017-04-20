odoo.define('web.basic_fields_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('basic_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    date: {string: "A date", type: "date", searchable: true},
                    datetime: {string: "A datetime", type: "datetime", searchable: true},
                    display_name: {string: "Displayed name", type: "char", searchable: true},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", searchable: true},
                    bar: {string: "Bar", type: "boolean", default: true, searchable: true},
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

    QUnit.module('FieldBoolean');

    QUnit.test('boolean field in form view', function (assert) {
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="bar"/></form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_boolean input:checked').length, 1,
            "checkbox should be checked");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_field_boolean input:checked').length, 1,
            "checkbox should still be checked");

        // uncheck the checkbox
        form.$('.o_field_boolean input:checked').click();
        assert.strictEqual(form.$('.o_field_boolean input:checked').length, 0,
            "checkbox should no longer be checked");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_field_boolean input:checked').length, 0,
            "checkbox should still no longer be checked");

        // switch to edit mode and test the opposite change
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_field_boolean input:checked').length, 0,
            "checkbox should still be unchecked");
        // check the checkbox by hitting the "enter" key after focusing it
        form.$('.o_field_boolean input')
            .trigger("focusin")
            .trigger({type: "keydown", which: $.ui.keyCode.ENTER})
            .trigger({type: "keyup", which: $.ui.keyCode.ENTER});
        assert.strictEqual(form.$('.o_field_boolean input:checked').length, 1,
            "checkbox should now be checked");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_field_boolean input:checked').length, 1,
            "checkbox should still be checked");
        form.destroy();
    });

    QUnit.test('boolean field in editable list view', function (assert) {
        assert.expect(11);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="bar"/></tree>',
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input').length, 5,
            "should have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input:checked').length, 4,
            "should have 4 checked input");

        // Edit a line
        var $cell = list.$('tr.o_data_row:has(.o_checkbox input:checked) td:not(.o_list_record_selector)').first();
        assert.ok($cell.find('.o_checkbox input:checked').prop('disabled'),
            "input should be disabled in readonly mode");
        $cell.click();
        assert.ok(!$cell.find('.o_checkbox input:checked').prop('disabled'),
            "input should not have the disabled property in edit mode");
        $cell.find('.o_checkbox input:checked').click();

        // save
        list.$buttons.find('.o_list_button_save').click();
        $cell = list.$('tr.o_data_row:has(.o_checkbox input:not(:checked)) td:not(.o_list_record_selector)').first();
        assert.ok($cell.find('.o_checkbox input:not(:checked)').prop('disabled'),
            "input should be disabled again");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input').length, 5,
            "should still have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input:checked').length, 3,
            "should now have only 3 checked input");

        // Re-Edit the line and fake-check the checkbox
        $cell.click();
        $cell.find('.o_checkbox input').click(); // Change the checkbox
        $cell.find('.o_checkbox input').click(); // Undo the change

        // Save
        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input').length, 5,
            "should still have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input:checked').length, 3,
            "should still have only 3 checked input");

        // Re-Edit the line to check the checkbox back
        $cell = list.$('tr.o_data_row:has(.o_checkbox input:not(:checked)) td:not(.o_list_record_selector)').first();
        $cell.click();
        $cell.find('.o_checkbox input:not(:checked)').click();

        // save
        list.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input').length, 5,
            "should still have 5 checkboxes");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) .o_checkbox input:checked').length, 4,
            "should now have 4 checked input back");
        list.destroy();
    });


    QUnit.module('FieldBooleanButton');

    QUnit.test('use custom terminology in form view', function (assert) {
        assert.expect(2);

        var terminology = {
            string_true: "Production Environment",
            hover_true: "Switch to test environment",
            string_false: "Test Environment",
            hover_false: "Switch to production environment"
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<div name="button_box" class="oe_button_box">' +
                        '<button type="object" class="oe_stat_button" icon="fa-check-square">' +
                            '<field name="bar" widget="boolean_button" options=\'{"terminology": ' +
                                JSON.stringify(terminology) + '}\'/>' +
                        '</button>' +
                    '</div>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_stat_text.o_not_hover:contains(Production Environment)').length, 1,
            "button should contain correct string");
        assert.strictEqual(form.$('.o_stat_text.o_hover:contains(Switch to test environment)').length, 1,
            "button should display correct string when hovering");
        form.destroy();
    });


    QUnit.module('FieldFloat');

    QUnit.test('float field when unset', function(assert) {
        assert.expect(1);

        var form = createView({
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

        assert.ok(form.$('.o_form_field').hasClass('o_form_field_empty'),
        'Non-set float field should be recognized as unset.');

        form.destroy();
    });

    QUnit.test('float fields use correct digit precision', function (assert) {
        assert.expect(1);

        var form = createView({
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
        assert.strictEqual(form.$('span.o_form_field_number:contains(0.4)').length, 1,
                            "should contain a number rounded to 1 decimal");
        form.destroy();
    });

    QUnit.test('float field in form view', function (assert) {
        assert.expect(5);

        var form = createView({
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

        assert.ok(!form.$('.o_form_field').hasClass('o_form_field_empty'),
            'Float field should be considered set for value 0.');
        assert.strictEqual(form.$('.o_form_field.o_form_field_number').first().text(), '0.000',
            'The value should be displayed properly.');

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input.o_form_input').val(), '0.000',
            'The value should be rendered with correct precision.');

        form.$('input.o_form_input').val('108.2458938598598').trigger('input');
        assert.strictEqual(form.$('input.o_form_input').val(), '108.2458938598598',
            'The value should not be formated yet.');

        form.$('input.o_form_input').val('18.8958938598598').trigger('input');
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field.o_form_field_number').first().text(), '18.896',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('float field in editable list view', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="qux" widget="float" digits="[5,3]"/>' +
                  '</tree>',
        });

        var zeroValues = list.$('td').filter(function () {return $(this).text() === '0.000';});
        assert.strictEqual(zeroValues.length, 2,
            'Unset float values should be rendered as zeros.');

        // switch to edit mode
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        $cell.click();

        assert.strictEqual(list.$('input.o_form_input').length, 1,
            'The view should have 1 input for editable float.');

        list.$('input.o_form_input').val('108.2458938598598').trigger('input');
        assert.strictEqual(list.$('input.o_form_input').val(), '108.2458938598598',
            'The value should not be formated yet.');

        list.$('input.o_form_input').val('18.8958938598598').trigger('input');
        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('.o_form_field.o_form_field_number').first().text(), '18.896',
            'The new value should be rounded properly.');

        list.destroy();
    });


    QUnit.module('EmailWidget');

    QUnit.test('email field in form view', function (assert) {
        assert.expect(7);

        var form = createView({
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

        var $mailtoLink = form.$('a.o_form_uri.o_form_field.o_text_overflow');
        assert.strictEqual($mailtoLink.length, 1,
            "should have a anchor with correct classes");
        assert.strictEqual($mailtoLink.text(), 'yop',
            "the value should be displayed properly");
        assert.strictEqual($mailtoLink.attr('href'), 'mailto:yop',
            "should have proper mailto prefix");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').length, 1,
            "should have an input for the email field");
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        form.$('input[type="text"].o_form_input.o_form_field').val('new').trigger('input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        $mailtoLink = form.$('a.o_form_uri.o_form_field.o_text_overflow');
        assert.strictEqual($mailtoLink.text(), 'new',
            "new value should be displayed properly");
        assert.strictEqual($mailtoLink.attr('href'), 'mailto:new',
            "should still have proper mailto prefix");

        form.destroy();
    });

    QUnit.test('email field in editable list view', function (assert) {
        assert.expect(10);

        var list = createView({
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
        assert.strictEqual($mailtoLink.first().attr('href'), 'mailto:yop',
            "should have proper mailto prefix");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        $cell.click();
        assert.ok($cell.parent().hasClass('o_selected_row'), 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        $cell.find('input').val('new').trigger('input');

        // save
        list.$buttons.find('.o_list_button_save').click();
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.ok(!$cell.parent().hasClass('o_selected_row'), 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'new',
            "value should be properly updated");
        $mailtoLink = list.$('a.o_form_uri.o_field_widget.o_text_overflow');
        assert.strictEqual($mailtoLink.length, 5,
            "should still have anchors with correct classes");
        assert.strictEqual($mailtoLink.first().attr('href'), 'mailto:new',
            "should still have proper mailto prefix");

        list.destroy();
    });


    QUnit.module('FieldChar');

    QUnit.test('char widget isValid method works', function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.required = true;
        var form = createView({
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

    QUnit.test('char field in form view', function (assert) {
        assert.expect(4);

        var form = createView({
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

        assert.strictEqual(form.$('.o_form_field').text(), 'yop',
            "the value should be displayed properly");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').length, 1,
            "should have an input for the char field");
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        form.$('input[type="text"].o_form_input.o_form_field').val('limbo').trigger('input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field').text(), 'limbo',
            'the new value should be displayed');
        form.destroy();
    });

    QUnit.test('char field in editable list view', function (assert) {
        assert.expect(6);

        var list = createView({
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
        $cell.click();
        assert.ok($cell.parent().hasClass('o_selected_row'), 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        $cell.find('input').val('brolo').trigger('input');

        // save
        list.$buttons.find('.o_list_button_save').click();
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.ok(!$cell.parent().hasClass('o_selected_row'), 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'brolo',
            "value should be properly updated");
        list.destroy();
    });


    QUnit.module('UrlWidget');

    QUnit.test('url widget in form view', function (assert) {
        assert.expect(8);

        var form = createView({
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

        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').length, 1,
            "should have a anchor with correct classes");
        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').attr('href'), 'yop',
            "should have proper href link");
        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').text(), 'yop',
            "the value should be displayed properly");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').length, 1,
            "should have an input for the char field");
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        form.$('input[type="text"].o_form_input.o_form_field').val('limbo').trigger('input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').length, 1,
            "should still have a anchor with correct classes");
        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').attr('href'), 'limbo',
            "should have proper new href link");
        assert.strictEqual(form.$('a.o_form_uri.o_form_field.o_text_overflow').text(), 'limbo',
            'the new value should be displayed');

        form.destroy();
    });

    QUnit.test('char field in editable list view', function (assert) {
        assert.expect(10);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" widget="url"/></tree>',
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').length, 5,
            "should have 5 cells");
        assert.strictEqual(list.$('a.o_form_uri.o_field_widget.o_text_overflow').length, 5,
            "should have 5 anchors with correct classes");
        assert.strictEqual(list.$('a.o_form_uri.o_field_widget.o_text_overflow').first().attr('href'), 'yop',
            "should have proper href link");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yop',
            "value should be displayed properly as text");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        $cell.click();
        assert.ok($cell.parent().hasClass('o_selected_row'), 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        $cell.find('input').val('brolo').trigger('input');

        // save
        list.$buttons.find('.o_list_button_save').click();
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.ok(!$cell.parent().hasClass('o_selected_row'), 'should not be in edit mode anymore');
        assert.strictEqual(list.$('a.o_form_uri.o_field_widget.o_text_overflow').length, 5,
            "should still have 5 anchors with correct classes");
        assert.strictEqual(list.$('a.o_form_uri.o_field_widget.o_text_overflow').first().attr('href'), 'brolo',
            "should have proper new href link");
        assert.strictEqual(list.$('a.o_form_uri.o_field_widget.o_text_overflow').first().text(), 'brolo',
            "value should be properly updated");

        list.destroy();
    });


    QUnit.module('FieldText');

    QUnit.test('text fields are correctly rendered', function (assert) {
        assert.expect(7);

        this.data.partner.fields.foo.type = 'text';
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(form.$('div.o_form_textarea').length, "should have a text area");
        assert.strictEqual(form.$('div.o_form_textarea').text(), 'yop', 'should be "yop" in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        var $textarea = form.$('.o_form_textarea textarea');
        assert.ok($textarea.length, "should have a text area");
        assert.strictEqual($textarea.val(), 'yop', 'should still be "yop" in edit');

        $textarea.val('hello').trigger('input');
        assert.strictEqual($textarea.val(), 'hello', 'should be "hello" after first edition');

        $textarea.val('hello world').trigger('input');
        assert.strictEqual($textarea.val(), 'hello world', 'should be "hello world" after second edition');

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('div.o_form_textarea').text(), 'hello world',
            'should be "hello world" after save');
        form.destroy();
    });

    QUnit.test('text fields in edit mode have correct height', function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.type = 'text';
        this.data.partner.records[0].foo = "f\nu\nc\nk\nm\ni\nl\ng\nr\no\nm";
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        var $field = form.$('div.o_list_text');

        assert.strictEqual($field.outerHeight(), $field[0].scrollHeight,
            "text field should not have a scroll bar");

        form.$buttons.find('.o_form_button_edit').click();

        var $textarea = form.$('textarea:first');

        // the difference is to take small calculation errors into account
        assert.strictEqual($textarea.innerHeight(), $textarea[0].scrollHeight,
            "textarea should not have a scroll bar");
        form.destroy();
    });


    QUnit.test('text field rendering in list view', function (assert) {
        assert.expect(1);

        var data = {
            foo: {
                fields: {foo: {string: "F", type: "text"}},
                records: [{id: 1, foo: "some text"}]
            },
        };
        var list = createView({
            View: ListView,
            model: 'foo',
            data: data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('tbody td.o_list_text:contains(some text)').length, 1,
            "should have a td with the .o_list_text class");
        list.destroy();
    });

    QUnit.test('field text in editable list view', function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.type = 'text';

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        list.$buttons.find('.o_list_button_add').click();

        assert.strictEqual(list.$('textarea').first().get(0), document.activeElement,
            "text area should have the focus");
        list.destroy();
    });

    QUnit.test('field changes are correctly debounced in text fields', function (assert) {
        var done = assert.async();
        assert.expect(5);

        this.data.partner.fields.foo.type = 'text';

        var def = $.Deferred();
        var nbNotifyChanges = 0;
        var form = createView({
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

        form.$buttons.find('.o_form_button_edit').click();

        form.$('textarea').val("1").trigger('input');
        assert.strictEqual(nbNotifyChanges, 0,
            "no event should have been triggered");
        form.$('textarea').val("12").trigger('input');
        assert.strictEqual(nbNotifyChanges, 0,
            "no event should have been triggered");

        return waitForChangeTriggered().then(function () {
            assert.strictEqual(nbNotifyChanges, 1,
                "one event should have been triggered");

            // add something in the textarea, then focus another input
            form.$('textarea').first().val("123").trigger('input');
            form.$('textarea').first().change();
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
                def = $.Deferred();
                return concurrency.delay(0);
            });
        }
    });

    QUnit.module('JournalDashboardGraph');

    QUnit.test('graph dashboard widget is rendered correctly', function (assert) {
        var done = assert.async();
        assert.expect(3);

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
        var kanban = createView({
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
        });

        // nvd3 seems to do a setTimeout(0) each time the addGraph function is
        // called, which is done twice in this case as there are 2 records.
        // for that reason, we need to do two setTimeout(0) as well here to ensure
        // that both graphs are rendered before starting to check if the rendering
        // is correct.
        concurrency.delay(0).then(function () {
            return concurrency.delay(0);
        }).then(function () {
            assert.strictEqual(kanban.$('.o_kanban_record:first() .o_graph_barchart').length, 1,
                "graph of first record should be a barchart");
            assert.strictEqual(kanban.$('.o_kanban_record:nth(1) .o_graph_linechart').length, 1,
                "graph of second record should be a linechart");

            // force a re-rendering of the first record (to check if the
            // previous rendered graph is correctly removed from the DOM)
            var firstRecordState = kanban.model.get(kanban.handle).data[0];
            return kanban.renderer.updateRecord(firstRecordState);
        }).then(function () {
            return concurrency.delay(0); // one graph is re-rendered
        }).then(function () {
            assert.strictEqual(kanban.$('.o_kanban_record:first() svg').length, 1,
                "there should be only one rendered graph by record");

            kanban.destroy();
            done();
        });

    });

    QUnit.module('AceEditor');

    QUnit.test('ace widget on text fields works', function (assert) {
        assert.expect(2);
        var done = assert.async();

        this.data.partner.fields.foo.type = 'text';
        testUtils.createAsyncView({
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

    QUnit.test('handle widget', function (assert) {
        assert.expect(6);

        this.data.partner.records[0].p = [2, 4];
        var form = createView({
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

        assert.strictEqual(form.$('span.o_row_handle').length, 2, "should have 2 handles");

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('td:first').hasClass('o_handle_cell'),
            "column widget should be displayed in css class");

        assert.ok(form.$('td span.o_row_handle').is(':visible'),
            "handle should be visible in readonly mode");

        form.$('td').eq(1).click();
        assert.strictEqual(form.$('td:first span.o_row_handle').length, 1,
            "content of the cell should have been replaced");
        form.destroy();
    });


    QUnit.module('FieldDate');

    QUnit.test('date field is empty if no date is set', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="date"/></form>',
            res_id: 4,
        });
        var $span = form.$('span.o_form_field');
        assert.strictEqual($span.length, 1, "should have one span in the form view");
        assert.strictEqual($span.text(), "", "and it should be empty");
        form.destroy();
    });

    QUnit.test('date field in form view', function (assert) {
        assert.expect(7);

        var form = createView({
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
                tzOffset: 120
            },
        });

        assert.strictEqual(form.$('.o_form_field_date').text(), '02/03/2017',
            'the date should be correctly displayed in readonly');

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        // click on the input and select another value
        form.$('.o_datepicker_input').click();
        assert.ok(form.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be open');
        form.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Month selection
        form.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Year selection
        form.$('.bootstrap-datetimepicker-widget .year:contains(2017)').click();
        form.$('.bootstrap-datetimepicker-widget .month').eq(1).click();  // February
        form.$('.day:contains(22)').click(); // select the 22 February
        assert.ok(!form.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/22/2017',
            'the selected date should be displayed in the input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field_date').text(), '02/22/2017',
            'the selected date should be displayed after saving');
        form.destroy();
    });

    QUnit.test('date field in editable list view', function (assert) {
        assert.expect(8);

        var list = createView({
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
                tzOffset: 0
            },
        });

        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        assert.strictEqual($cell.text(), '02/03/2017',
            'the date should be displayed correctly in readonly');
        $cell.click();

        assert.strictEqual(list.$('input.o_datepicker_input').length, 1,
            "the view should have a date input for editable mode");

        assert.strictEqual(list.$('input.o_datepicker_input').get(0), document.activeElement,
            "date input should have the focus");

        assert.strictEqual(list.$('input.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        // click on the input and select another value
        list.$('input.o_datepicker_input').click();
        assert.ok(list.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be open');
        list.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Month selection
        list.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Year selection
        list.$('.bootstrap-datetimepicker-widget .year:contains(2017)').click();
        list.$('.bootstrap-datetimepicker-widget .month').eq(1).click();  // February
        list.$('.day:contains(22)').click(); // select the 22 February
        assert.ok(!list.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');
        assert.strictEqual(list.$('.o_datepicker_input').val(), '02/22/2017',
            'the selected date should be displayed in the input');

        // save
        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('tr.o_data_row td:not(.o_list_record_selector)').text(), '02/22/2017',
            'the selected date should be displayed after saving');

        list.destroy();
    });

    QUnit.test('date field remove value', function (assert) {
        assert.expect(4);

        var form = createView({
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
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/03/2017',
            'the date should be correct in edit mode');

        $('.o_datepicker_input').val('').trigger('input').trigger('change');
        assert.ok(!form.$('.o_datepicker_input').val());

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field_date').text(), '',
            'the selected date should be displayed after saving');
        form.destroy();
    });


    QUnit.module('FieldDatetime');

    QUnit.test('datetime field in form view', function(assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="datetime"/></form>',
            res_id: 1,
            translateParameters: {  // Avoid issues due to localization formats
                date_format: '%m/%d/%Y',
                time_format: '%H:%M:%S',
            },
            session: {
                tzOffset: 120
            },
        });

        var expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
        assert.strictEqual(form.$('.o_form_field_date').text(), expectedDateString,
            'the datetime should be correctly displayed in readonly');

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_datepicker_input').val(), expectedDateString,
            'the datetime should be correct in edit mode');
        // click on the input and select 22 February at 8:23:33
        form.$('.o_datepicker_input').click();
        assert.ok(form.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be open');
        form.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Month selection
        form.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Year selection
        form.$('.bootstrap-datetimepicker-widget .year:contains(2017)').click();
        form.$('.bootstrap-datetimepicker-widget .month').eq(3).click();  // April
        form.$('.bootstrap-datetimepicker-widget .day:contains(22)').click();
        form.$('.bootstrap-datetimepicker-widget .fa-clock-o').click();
        form.$('.bootstrap-datetimepicker-widget .timepicker-hour').click();
        form.$('.bootstrap-datetimepicker-widget .hour:contains(08)').click();
        form.$('.bootstrap-datetimepicker-widget .timepicker-minute').click();
        form.$('.bootstrap-datetimepicker-widget .minute:contains(25)').click();
        form.$('.bootstrap-datetimepicker-widget .timepicker-second').click();
        form.$('.bootstrap-datetimepicker-widget .second:contains(35)').click();
        form.$('.bootstrap-datetimepicker-widget .fa-times').click();  // close
        assert.ok(!form.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');

        var newExpectedDateString = "04/22/2017 08:25:35";
        assert.strictEqual(form.$('.o_datepicker_input').val(), newExpectedDateString,
            'the selected date should be displayed in the input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field_date').text(), newExpectedDateString,
            'the selected date should be displayed after saving');

        form.destroy();
    });

    QUnit.test('datetime field in editable list view', function (assert) {
        assert.expect(8);

        var list = createView({
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
                tzOffset: 120
            },
        });

        var expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        assert.strictEqual($cell.text(), expectedDateString,
            'the datetime should be correctly displayed in readonly');

        // switch to edit mode
        $cell.click();
        assert.strictEqual(list.$('input.o_datepicker_input').length, 1,
            "the view should have a date input for editable mode");

        assert.strictEqual(list.$('input.o_datepicker_input').get(0), document.activeElement,
            "date input should have the focus");

        assert.strictEqual(list.$('input.o_datepicker_input').val(), expectedDateString,
            'the date should be correct in edit mode');

        // click on the input and select 22 February at 8:23:33
        list.$('input.o_datepicker_input').click();
        assert.ok(list.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be open');
        list.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Month selection
        list.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Year selection
        list.$('.bootstrap-datetimepicker-widget .year:contains(2017)').click();
        list.$('.bootstrap-datetimepicker-widget .month').eq(3).click();  // April
        list.$('.bootstrap-datetimepicker-widget .day:contains(22)').click();
        list.$('.bootstrap-datetimepicker-widget .fa-clock-o').click();
        list.$('.bootstrap-datetimepicker-widget .timepicker-hour').click();
        list.$('.bootstrap-datetimepicker-widget .hour:contains(08)').click();
        list.$('.bootstrap-datetimepicker-widget .timepicker-minute').click();
        list.$('.bootstrap-datetimepicker-widget .minute:contains(25)').click();
        list.$('.bootstrap-datetimepicker-widget .timepicker-second').click();
        list.$('.bootstrap-datetimepicker-widget .second:contains(35)').click();
        list.$('.bootstrap-datetimepicker-widget .fa-times').click();  // close
        assert.ok(!list.$('.bootstrap-datetimepicker-widget').length, 'datepicker should be closed');

        var newExpectedDateString = "04/22/2017 08:25:35";
        assert.strictEqual(list.$('.o_datepicker_input').val(), newExpectedDateString,
            'the selected datetime should be displayed in the input');

        // save
        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('tr.o_data_row td:not(.o_list_record_selector)').text(), newExpectedDateString,
            'the selected datetime should be displayed after saving');

        list.destroy();
    });

    QUnit.test('datetime field remove value', function (assert) {
        assert.expect(4);

        var form = createView({
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
                tzOffset: 120
            },
        });

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_datepicker_input').val(), '02/08/2017 12:00:00',
            'the date time should be correct in edit mode');

        $('.o_datepicker_input').val('').trigger('input').trigger('change');
        assert.ok(!form.$('.o_datepicker_input').val());

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field_date').text(), '',
            'the selected date should be displayed after saving');
        form.destroy();
    });


    QUnit.module('FieldMonetary');

    QUnit.test('monetary field in form view', function(assert) {
        assert.expect(5);

        var form = createView({
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
        assert.strictEqual(form.$('.o_form_field').first().text(), '$\u00a09.10',
            'The value should be displayed properly.');

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input.o_form_input').val(), '9.10',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(form.$('input.o_form_input').parent().children().first().text(), '$',
            'The input should be preceded by a span containing the currency symbol.');

        form.$('input.o_form_input').val('108.2458938598598').trigger('input');
        assert.strictEqual(form.$('input.o_form_input').val(), '108.2458938598598',
            'The value should not be formated yet.');

        form.$buttons.find('.o_form_button_save').click();
        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_form_field').first().text(), '$\u00a0108.25',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('monetary field with currency symbol after', function(assert) {
        assert.expect(5);

        var form = createView({
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
        assert.strictEqual(form.$('.o_form_field').first().text(), '0.00\u00a0€',
            'The value should be displayed properly.');

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input.o_form_input').val(), '0.00',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(form.$('input.o_form_input').parent().children().eq(1).text(), '€',
            'The input should be followed by a span containing the currency symbol.');

        form.$('input.o_form_input').val('108.2458938598598').trigger('input');
        assert.strictEqual(form.$('input.o_form_input').val(), '108.2458938598598',
            'The value should not be formated yet.');

        form.$buttons.find('.o_form_button_save').click();
        // Non-breaking space between the currency and the amount
        assert.strictEqual(form.$('.o_form_field').first().text(), '108.25\u00a0€',
            'The new value should be rounded properly.');

        form.destroy();
    });

    QUnit.test('monetary field in editable list view', function (assert) {
        assert.expect(9);

        var list = createView({
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

        var dollarValues = list.$('td').filter(function() {return _.str.include($(this).text(), '$')});
        assert.strictEqual(dollarValues.length, 1,
            'Only one line has dollar as a currency.');

        var euroValues = list.$('td').filter(function() {return _.str.include($(this).text(), '€')});
        assert.strictEqual(euroValues.length, 1,
            'One one line has euro as a currency.');

        var zeroValues = list.$('td').filter(function() {return _.str.include($(this).text(), '0.00')});
        assert.strictEqual(zeroValues.length, 2,
            'Unset float values should be rendered as zeros.');

        // switch to edit mode
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector):contains($)');
        $cell.click();

        assert.strictEqual($cell.children().length, 1,
            'The cell td should only contain the special div of monetary widget.');
        assert.strictEqual(list.$('input.o_form_input').length, 1,
            'The view should have 1 input for editable monetary float.');
        assert.strictEqual(list.$('input.o_form_input').val(), '9.10',
            'The input should be rendered without the currency symbol.');
        assert.strictEqual(list.$('input.o_form_input').parent().children().first().text(), '$',
            'The input should be preceded by a span containing the currency symbol.');

        list.$('input.o_form_input').val('108.2458938598598').trigger('input');
        assert.strictEqual(list.$('input.o_form_input').val(), '108.2458938598598',
            'The typed value should be correctly displayed.');

        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('tr.o_data_row td:not(.o_list_record_selector):contains($)').text(), '$\u00a0108.25',
            'The new value should be rounded properly.');

        list.destroy();
    });

    QUnit.test('monetary field with real monetary field in model', function (assert) {
        assert.expect(4);

        this.data.partner.fields.qux.type = "monetary";

        this.data.partner.onchanges = {
            bar: function (obj) {
                obj.qux = obj.bar ? 100 : obj.qux;
            },
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux"/>' +
                        '<field name="currency_id"/>' +
                        '<field name="bar"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });

        assert.strictEqual(form.$('.o_form_field_monetary').html(), "$&nbsp;9.10",
            "readonly value should contain the currency");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_form_field_monetary > input').val(), "9.10",
            "input value in edition should only contain the value, without the currency");

        form.$('input[type="checkbox"]').click(); // Change the field on which the monetary depends
        assert.strictEqual(form.$('.o_form_field_monetary > input').length, 1,
            "After the onchange, the monetary <input/> should not have been duplicated");

        var $dropdown = form.$('.o_form_field_many2one input').autocomplete('widget');
        form.$('.o_form_field_many2one input').click();
        $dropdown.find('li:not(.o_m2o_dropdown_option):last').mouseenter().click();
        assert.strictEqual(form.$('.o_form_field_monetary > span').html(), "€",
            "After currency change, the monetary field currency should have been updated");

        form.destroy();
    });

    QUnit.module('FieldInteger');

    QUnit.test('integer field when unset', function(assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="int_field"/></form>',
            res_id: 4,
        });

        assert.ok(form.$('.o_form_field').hasClass('o_form_field_empty'),
            'Non-set integer field should be recognized as unset.');

        form.destroy();
    });

    QUnit.test('integer field in form view', function(assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="int_field"/></form>',
            res_id: 2,
        });

        assert.ok(!form.$('.o_form_field').hasClass('o_form_field_empty'),
            'Integer field should be considered set for value 0.');

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input.o_form_input').val(), '0',
            'The value should be rendered correctly in edit mode.')

        form.$('input.o_form_input').val('-18').trigger('input');
        assert.strictEqual(form.$('input.o_form_input').val(), '-18',
            'The value should be correctly displayed in the input.')

        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field').text(), '-18',
            'The new value should be saved and displayed properly.')

        form.destroy();
    });

    QUnit.test('integer field in editable list view', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field"/>' +
                  '</tree>',
        });

        var zeroValues = list.$('td').filter(function() {return $(this).text() === '0'});
        assert.strictEqual(zeroValues.length, 1,
            'Unset integer values should not be rendered as zeros.');

        // switch to edit mode
        var $cell = list.$('tr.o_data_row td:not(.o_list_record_selector)').first();
        $cell.click();

        assert.strictEqual(list.$('input.o_form_input').length, 1,
            'The view should have 1 input for editable integer.')

        list.$('input.o_form_input').val('-28').trigger('input');
        assert.strictEqual(list.$('input.o_form_input').val(), '-28',
            'The value should be displayed properly in the input.')

        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('td:not(.o_list_record_selector)').first().text(), '-28',
            'The new value should be saved and displayed properly.')

        list.destroy();
    });


    QUnit.module('FieldFloatTime');

    QUnit.test('float_time field in form view', function(assert) {
        assert.expect(5);

        var form = createView({
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
        assert.strictEqual(form.$('.o_form_field').first().text(), '09:06',
            'The formatted time value should be displayed properly.')

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input.o_form_input').val(), '09:06',
            'The value should be rendered correctly in the input.')

        form.$('input.o_form_input').val('-11:48').trigger('input');
        assert.strictEqual(form.$('input.o_form_input').val(), '-11:48',
            'The new value should be displayed properly in the input.')

        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field').first().text(), '-11:48',
            'The new value should be saved and displayed properly.')

        form.destroy();
    });


    QUnit.module('PhoneWidget');

    QUnit.test('phone field in form view on extra small screens', function (assert) {
        assert.expect(7);

        var form = createView({
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
                    size_class: 0, // Screen XS
                    SIZES: { XS: 0, SM: 1, MD: 2, LG: 3 },
                }
            },
        });

        var $phoneLink = form.$('a.o_form_uri.o_form_field.o_text_overflow');
        assert.strictEqual($phoneLink.length, 1,
            "should have a anchor with correct classes");
        assert.strictEqual($phoneLink.text(), 'y\u00ADop',
            "value should be displayed properly as text with the skype obfuscation");
        assert.strictEqual($phoneLink.attr('href'), 'tel:yop',
            "should have proper tel prefix");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').length, 1,
            "should have an input for the phone field");
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        form.$('input[type="text"].o_form_input.o_form_field').val('new').trigger('input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        $phoneLink = form.$('a.o_form_uri.o_form_field.o_text_overflow');
        assert.strictEqual($phoneLink.text(), 'n\u00ADew',
            "new value should be displayed properly as text with the skype obfuscation");
        assert.strictEqual($phoneLink.attr('href'), 'tel:new',
            "should still have proper tel prefix");

        form.destroy();
    });

    QUnit.test('phone field in editable list view on extra small screens', function(assert) {
        assert.expect(10);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"  widget="phone"/></tree>',
            config: {
                device: {
                    size_class: 0, // Screen XS
                    SIZES: { XS: 0, SM: 1, MD: 2, LG: 3 },
                }
            },
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').length, 5,
            "should have 5 cells");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'y\u00ADop',
            "value should be displayed properly as text with the skype obfuscation");

        var $phoneLink = list.$('a.o_form_uri.o_field_widget.o_text_overflow');
        assert.strictEqual($phoneLink.length, 5,
            "should have anchors with correct classes");
        assert.strictEqual($phoneLink.first().attr('href'), 'tel:yop',
            "should have proper tel prefix");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        $cell.click();
        assert.ok($cell.parent().hasClass('o_selected_row'), 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        $cell.find('input').val('new').trigger('input');

        // save
        list.$buttons.find('.o_list_button_save').click();
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.ok(!$cell.parent().hasClass('o_selected_row'), 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'n\u00ADew',
            "value should be properly updated");
        $phoneLink = list.$('a.o_form_uri.o_field_widget.o_text_overflow');
        assert.strictEqual($phoneLink.length, 5,
            "should still have anchors with correct classes");
        assert.strictEqual($phoneLink.first().attr('href'), 'tel:new',
            "should still have proper tel prefix");

        list.destroy();
    });

    QUnit.test('phone field in form view on normal screens', function (assert) {
        // The behavior of this widget is completely altered by crm_voip so this
        // test is irrelevant and fails if crm_voip is installed. The enterprise
        // module is responsible for testing its own behavior in its own tests.
        if ('crm.voip' in odoo.__DEBUG__.services) {
            assert.expect(0);
            return;
        }

        assert.expect(5);

        var form = createView({
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
                    size_class: 1, // Screen SM
                    SIZES: { XS: 0, SM: 1, MD: 2, LG: 3 },
                }
            },
        });

        var $phone = form.$('span.o_form_field.o_text_overflow:not(.o_form_uri)');
        assert.strictEqual($phone.length, 1,
            "should have a simple span rather than a link");
        assert.strictEqual($phone.text(), 'yop',
            "value should be displayed properly as text without skype obfuscation");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').length, 1,
            "should have an input for the phone field");
        assert.strictEqual(form.$('input[type="text"].o_form_input.o_form_field').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        form.$('input[type="text"].o_form_input.o_form_field').val('new').trigger('input');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('span.o_form_field.o_text_overflow:not(.o_form_uri)').text(), 'new',
            "new value should be displayed properly as text without skype obfuscation");

        form.destroy();
    });

    QUnit.test('phone field in editable list view on normal screens', function(assert) {
        // The behavior of this widget is completely altered by crm_voip so this
        // test is irrelevant and fails if crm_voip is installed. The enterprise
        // module is responsible for testing its own behavior in its own tests.
        if ('crm.voip' in odoo.__DEBUG__.services) {
            assert.expect(0);
            return;
        }

        assert.expect(8);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"  widget="phone"/></tree>',
            config: {
                device: {
                    size_class: 1, // Screen SM
                    SIZES: { XS: 0, SM: 1, MD: 2, LG: 3 },
                }
            },
        });

        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').length, 5,
            "should have 5 cells");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yop',
            "value should be displayed properly as text without skype obfuscation");

        assert.strictEqual(list.$('span.o_field_widget.o_text_overflow:not(.o_form_uri)').length, 5,
            "should have spans with correct classes");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        $cell.click();
        assert.ok($cell.parent().hasClass('o_selected_row'), 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        $cell.find('input').val('new').trigger('input');

        // save
        list.$buttons.find('.o_list_button_save').click();
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.ok(!$cell.parent().hasClass('o_selected_row'), 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'new',
            "value should be properly updated");
        assert.strictEqual(list.$('span.o_field_widget.o_text_overflow:not(.o_form_uri)').length, 5,
            "should still have spans with correct classes");

        list.destroy();
    });


    QUnit.module('PriorityWidget');

    QUnit.test('priority widget when not set', function (assert) {
        assert.expect(4);

        var form = createView({
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

        assert.strictEqual(form.$('.o_form_field.o_priority:not(.o_form_field_empty)').length, 1,
            "widget should be considered set, even though there is no value for this field");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 0,
            "should have no full star since there is no value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 2,
            "should have two empty stars since there is no value");

        form.destroy();
    });

    QUnit.test('priority widget in form view', function (assert) {
        assert.expect(22);

        var form = createView({
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

        assert.strictEqual(form.$('.o_form_field.o_priority:not(.o_form_field_empty)').length, 1,
            "widget should be considered set");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should have one empty star since the value is the second value");

        // hover last star
        form.$('.o_form_field.o_priority a.o_priority_star.fa-star-o').last().trigger('mouseover');
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 2,
            "should temporary have two full stars since we are hovering the third value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 0,
            "should temporary have no empty star since we are hovering the third value");

        // Here we should test with mouseout, but currently the effect associated with it
        // occurs in a setTimeout after 200ms so it's not trivial to test it here.

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should still have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should still have one empty star since the value is the second value");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should still have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should still have one empty star since the value is the second value");

        // switch to edit mode to check that the new value was properly written
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 1,
            "should still have one full star since the value is the second value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 1,
            "should still have one empty star since the value is the second value");

        // click on the second star in edit mode
        form.$('.o_form_field.o_priority a.o_priority_star.fa-star-o').last().click();

        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(form.$('.o_form_field.o_priority').find('a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        form.destroy();
    });

    QUnit.test('priority widget in editable list view', function(assert) {
        assert.expect(25);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="selection" widget="priority"/></tree>',
        });

        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority:not(.o_form_field_empty)').length, 1,
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
        $cell.click();
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should have two stars for representing each possible value: no star, one star and two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 1,
            "should have one full star since the value is the second value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 1,
            "should have one empty star since the value is the second value");

        // save
        list.$buttons.find('.o_list_button_save').click();
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
        list.$('.o_priority a.o_priority_star.fa-star').first().click();

        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 0,
            "should now have no full star since the value is the first value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 2,
            "should now have two empty stars since the value is the first value");

        // re-enter edit mode to force re-rendering the widget to check if the value was correctly saved
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        $cell.click();

        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star').length, 0,
            "should now only have no full star since the value is the first value");
        assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.o_priority_star.fa-star-o').length, 2,
            "should now have two empty stars since the value is the first value");

        // Click on second star in edit mode
        list.$('.o_priority a.o_priority_star.fa-star-o').last().click();

        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        // save
        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star').length, 2,
            "should still have two stars");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star').length, 2,
            "should now have two full stars since the value is the third value");
        assert.strictEqual(list.$('.o_data_row').last().find('.o_priority a.o_priority_star.fa-star-o').length, 0,
            "should now have no empty star since the value is the third value");

        list.destroy();
    });


    QUnit.module('StateSelection Widget');

    QUnit.test('state_selection widget in form view', function (assert) {
        assert.expect(21);

        var form = createView({
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
        });

        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_red').length, 1,
            "should have one red status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_green').length, 0,
            "should not have one green status since selection is the second, blocked state");
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        form.$('.o_form_field.o_selection .o_status').first().click();
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible').length, 1,
            "there should be a dropdown");
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible li').length, 2,
            "there should be two options in the dropdown");

        // Click on the first option, "Normal"
        form.$('ul.dropdown-menu.state:visible li').first().click();
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown anymore");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_red').length, 0,
            "should not have one red status since selection is the first, normal state");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_green').length, 0,
            "should not have one green status since selection is the first, normal state");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status').length, 1,
            "should have one grey status since selection is the first, normal state");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible').length, 0,
            "there should still not be a dropdown");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_red').length, 0,
            "should still not have one red status since selection is the first, normal state");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_green').length, 0,
            "should still not have one green status since selection is the first, normal state");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status').length, 1,
            "should still have one grey status since selection is the first, normal state");

        // Click on the status button to make the dropdown appear
        form.$('.o_form_field.o_selection .o_status').first().click();
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible').length, 1,
            "there should be a dropdown");
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible li').length, 2,
            "there should be two options in the dropdown");

        // Click on the last option, "Done"
        form.$('ul.dropdown-menu.state:visible li').last().click();
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown anymore");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_red').length, 0,
            "should not have one red status since selection is the third, done state");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_green').length, 1,
            "should have one green status since selection is the third, done state");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('ul.dropdown-menu.state:visible').length, 0,
            "there should still not be a dropdown anymore");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_red').length, 0,
            "should still not have one red status since selection is the third, done state");
        assert.strictEqual(form.$('.o_form_field.o_selection > a span.o_status.o_status_green').length, 1,
            "should still have one green status since selection is the third, done state");

        form.destroy();
    });

    QUnit.test('state_selection widget in editable list view', function (assert) {
        assert.expect(32);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="selection" widget="state_selection"/>' +
                  '</tree>',
        });

        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status').length, 5,
            "should have five status selection widgets");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_red').length, 1,
            "should have one red status");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_green').length, 1,
            "should have one green status");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        var $cell = list.$('tbody td.o_state_selection_cell').first();
        list.$('.o_state_selection_cell .o_selection > a span.o_status').first().click();
        assert.ok(!$cell.parent().hasClass('o_selected_row'),
            'should not be in edit mode since we clicked on the state selection widget');
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 1,
            "there should be a dropdown");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible li').length, 2,
            "there should be two options in the dropdown");

        // Click on the first option, "Normal"
        list.$('ul.dropdown-menu.state:visible li').first().click();
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status').length, 5,
            "should still have five status selection widgets");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_red').length, 0,
            "should now have no red status");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_green').length, 1,
            "should still have one green status");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown");

        // switch to edit mode and check the result
        $cell = list.$('tbody td.o_state_selection_cell').first();
        $cell.click();
        assert.ok($cell.parent().hasClass('o_selected_row'),
            'should now be in edit mode');
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status').length, 5,
            "should still have five status selection widgets");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_red').length, 0,
            "should now have no red status");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_green').length, 1,
            "should still have one green status");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        list.$('.o_state_selection_cell .o_selection > a span.o_status').first().click();
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 1,
            "there should be a dropdown");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible li').length, 2,
            "there should be two options in the dropdown");

        // Click on another row
        var $firstCell = list.$('tbody td.o_state_selection_cell').first();
        var $lastCell = list.$('tbody td.o_state_selection_cell').last();
        $lastCell.click();
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown anymore");
        assert.ok(!$firstCell.parent().hasClass('o_selected_row'),
            'first row should not be in edit mode anymore');
        assert.ok($lastCell.parent().hasClass('o_selected_row'),
            'last row should be in edit mode');

        // Click on the last status button to make the dropdown appear
        list.$('.o_state_selection_cell .o_selection > a span.o_status').last().click();
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 1,
            "there should be a dropdown");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible li').length, 2,
            "there should be two options in the dropdown");

        // Click on the last option, "Done"
        list.$('ul.dropdown-menu.state:visible li').last().click();
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown anymore");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status').length, 5,
            "should still have five status selection widgets");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_red').length, 0,
            "should still have no red status");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_green').length, 2,
            "should now have two green status");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown");

        // save
        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status').length, 5,
            "should have five status selection widgets");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_red').length, 0,
            "should have no red status");
        assert.strictEqual(list.$('.o_state_selection_cell .o_selection > a span.o_status.o_status_green').length, 2,
            "should have two green status");
        assert.strictEqual(list.$('ul.dropdown-menu.state:visible').length, 0,
            "there should not be a dropdown");

        list.destroy();
    });


    QUnit.module('LabelSelectionWidget');

    QUnit.test('label_selection widget in form view', function (assert) {
        assert.expect(12);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="selection" widget="label_selection" ' +
                            ' options="{\'classes\': {\'normal\': \'default\', \'blocked\': \'warning\',\'done\': \'success\'}}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_form_field.label.label-warning').length, 1,
            "should have a warning status label since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-default').length, 0,
            "should not have a default status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-success').length, 0,
            "should not have a success status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-warning').text(), 'Blocked',
            "the label should say 'Blocked' since this is the label value for that state");

        // // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_field.label.label-warning').length, 1,
            "should have a warning status label since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-default').length, 0,
            "should not have a default status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-success').length, 0,
            "should not have a success status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-warning').text(), 'Blocked',
            "the label should say 'Blocked' since this is the label value for that state");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field.label.label-warning').length, 1,
            "should have a warning status label since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-default').length, 0,
            "should not have a default status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-success').length, 0,
            "should not have a success status since selection is the second, blocked state");
        assert.strictEqual(form.$('.o_form_field.label.label-warning').text(), 'Blocked',
            "the label should say 'Blocked' since this is the label value for that state");

        form.destroy();
    });

    QUnit.test('label_selection widget in editable list view', function(assert) {
        assert.expect(21);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="selection" widget="label_selection"' +
                    ' options="{\'classes\': {\'normal\': \'default\', \'blocked\': \'warning\',\'done\': \'success\'}}"/>' +
                  '</tree>',
        });

        assert.strictEqual(list.$('.o_field_widget.label:not(:empty)').length, 3,
            "should have three visible status labels");
        assert.strictEqual(list.$('.o_field_widget.label.label-warning').length, 1,
            "should have one warning status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-warning').text(), 'Blocked',
            "the warning label should read 'Blocked'");
        assert.strictEqual(list.$('.o_field_widget.label.label-default').length, 1,
            "should have one default status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-default').text(), 'Normal',
            "the default label should read 'Normal'");
        assert.strictEqual(list.$('.o_field_widget.label.label-success').length, 1,
            "should have one success status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-success').text(), 'Done',
            "the success label should read 'Done'");

        // switch to edit mode and check the result
        list.$('tbody td:not(.o_list_record_selector)').first().click();
        assert.strictEqual(list.$('.o_field_widget.label:not(:empty)').length, 3,
            "should have three visible status labels");
        assert.strictEqual(list.$('.o_field_widget.label.label-warning').length, 1,
            "should have one warning status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-warning').text(), 'Blocked',
            "the warning label should read 'Blocked'");
        assert.strictEqual(list.$('.o_field_widget.label.label-default').length, 1,
            "should have one default status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-default').text(), 'Normal',
            "the default label should read 'Normal'");
        assert.strictEqual(list.$('.o_field_widget.label.label-success').length, 1,
            "should have one success status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-success').text(), 'Done',
            "the success label should read 'Done'");

        // save and check the result
        list.$buttons.find('.o_list_button_save').click();
        assert.strictEqual(list.$('.o_field_widget.label:not(:empty)').length, 3,
            "should have three visible status labels");
        assert.strictEqual(list.$('.o_field_widget.label.label-warning').length, 1,
            "should have one warning status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-warning').text(), 'Blocked',
            "the warning label should read 'Blocked'");
        assert.strictEqual(list.$('.o_field_widget.label.label-default').length, 1,
            "should have one default status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-default').text(), 'Normal',
            "the default label should read 'Normal'");
        assert.strictEqual(list.$('.o_field_widget.label.label-success').length, 1,
            "should have one success status label");
        assert.strictEqual(list.$('.o_field_widget.label.label-success').text(), 'Done',
            "the success label should read 'Done'");

        list.destroy();
    });


    QUnit.module('StatInfo');

    QUnit.test('statinfo widget in form view', function (assert) {
        assert.expect(9);

        var form = createView({
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

        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            'int_field', "should have 'int_field' as text");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should still have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should still have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            'int_field', "should have 'int_field' as text");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            'int_field', "should have 'int_field' as text");

        form.destroy();
    });

    QUnit.test('statinfo widget in form view with specific label_field', function (assert) {
        assert.expect(9);

        var form = createView({
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

        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            'yop', "should have 'yop' as text, since it is the value of field foo");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should still have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should still have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            'yop', "should have 'yop' as text, since it is the value of field foo");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            'yop', "should have 'yop' as text, since it is the value of field foo");

        form.destroy();
    });

    QUnit.test('statinfo widget in form view with no label', function (assert) {
        assert.expect(9);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<button class="oe_stat_button" name="items"  type="object" icon="fa-gear">' +
                                '<field string="Useful stat button" name="int_field" widget="statinfo" ' +
                                        'options="{\'nolabel\': \'true\'}"/>' +
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

        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            '', "should not have any label");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should still have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should still have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            '', "should not have any label");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info').length, 1,
            "should have one stat button");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_value').text(),
            '10', "should have 10 as value");
        assert.strictEqual(form.$('.oe_stat_button .o_form_field.o_stat_info .o_stat_text').text(),
            '', "should not have any label");

        form.destroy();
    });


    QUnit.module('PercentPie');

    QUnit.test('percentpie widget in form view with value < 50%', function (assert) {
        assert.expect(12);

        var form = createView({
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

        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie').length, 1,
            "should have a pie chart");
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_pie_value').text(),
            '10%', "should have 10% as pie value since int_field=10");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').first().attr('style'),
            'transform: rotate(180deg);'), "left mask should be covering the whole left side of the pie");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').last().attr('style'),
            'transform: rotate(36deg);'), "right mask should be rotated from 360*(10/100) = 36 degrees");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie').length, 1,
            "should have a pie chart");
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_pie_value').text(),
            '10%', "should have 10% as pie value since int_field=10");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').first().attr('style'),
            'transform: rotate(180deg);'), "left mask should be covering the whole left side of the pie");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').last().attr('style'),
            'transform: rotate(36deg);'), "right mask should be rotated from 360*(10/100) = 36 degrees");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie').length, 1,
            "should have a pie chart");
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_pie_value').text(),
            '10%', "should have 10% as pie value since int_field=10");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').first().attr('style'),
            'transform: rotate(180deg);'), "left mask should be covering the whole left side of the pie");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').last().attr('style'),
            'transform: rotate(36deg);'), "right mask should be rotated from 360*(10/100) = 36 degrees");

        form.destroy();
    });

    QUnit.test('percentpie widget in form view with value > 50%', function (assert) {
        assert.expect(12);

        var form = createView({
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

        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie').length, 1,
            "should have a pie chart");
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_pie_value').text(),
            '80%', "should have 80% as pie value since int_field=80");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').first().attr('style'),
            'transform: rotate(288deg);'), "left mask should be rotated from 360*(80/100) = 288 degrees");
        assert.ok(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').last().hasClass('o_full'),
            "right mask should be hidden since the value > 50%");

        // switch to edit mode and check the result
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie').length, 1,
            "should have a pie chart");
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_pie_value').text(),
            '80%', "should have 80% as pie value since int_field=80");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').first().attr('style'),
            'transform: rotate(288deg);'), "left mask should be rotated from 360*(80/100) = 288 degrees");
        assert.ok(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').last().hasClass('o_full'),
            "right mask should be hidden since the value > 50%");

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie').length, 1,
            "should have a pie chart");
        assert.strictEqual(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_pie_value').text(),
            '80%', "should have 80% as pie value since int_field=80");
        assert.ok(_.str.include(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').first().attr('style'),
            'transform: rotate(288deg);'), "left mask should be rotated from 360*(80/100) = 288 degrees");
        assert.ok(form.$('.o_form_field_percent_pie.o_form_field .o_pie .o_mask').last().hasClass('o_full'),
            "right mask should be hidden since the value > 50%");

        form.destroy();
    });

    // TODO: This test would pass without any issue since all the classes and
    //       custom style attributes are correctly set on the widget in list
    //       view, but since the less itself for this widget currently only
    //       applies inside the form view, the widget is unusable. This test can
    //       be uncommented when we refactor the less files so that this widget
    //       stylesheet applies in both form and list view.
    // QUnit.test('percentpie widget in editable list view', function(assert) {
    //     assert.expect(10);
    //
    //     var list = createView({
    //         View: ListView,
    //         model: 'partner',
    //         data: this.data,
    //         arch: '<tree editable="bottom">' +
    //                 '<field name="foo"/>' +
    //                 '<field name="int_field" widget="percentpie"/>' +
    //               '</tree>',
    //     });
    //
    //     assert.strictEqual(list.$('.o_form_field_percent_pie .o_pie').length, 5,
    //         "should have five pie charts");
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole left side of the pie");
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // switch to edit mode and check the result
    //     list.$('tbody td:not(.o_list_record_selector)').first().click();
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // save
    //     list.$buttons.find('.o_list_button_save').click();
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(list.$('.o_form_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     list.destroy();
    // });


    QUnit.module('FieldDomain');

    QUnit.test('basic domain field usage is ok', function (assert) {
        assert.expect(6);

        this.data.partner.records[0].foo = "[]";

        var form = createView({
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
        form.$buttons.find('.o_form_button_edit').click();

        // As the domain is empty, there should be a button to add the first
        // domain part
        var $domain = form.$(".o_form_field_domain");
        var $domainAddFirstNodeButton = $domain.find(".o_domain_add_first_node_button");
        assert.equal($domainAddFirstNodeButton.length, 1,
            "there should be a button to create first domain element");

        // Clicking on the button should add the [["id", "=", "1"]] domain, so
        // there should be a field selector in the DOM
        $domainAddFirstNodeButton.click();
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1,
            "there should be a field selector");

        // Focusing the field selector input should open the field selector
        // popover
        $fieldSelector.trigger('focusin');
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"),
            "field selector popover should be visible");

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
        $colorIndex.click();
        $domain.find(".o_domain_leaf_value_input").val(2).change();
        assert.equal($domain.find(".o_domain_show_selection_button").text().trim().substr(0, 2), "1 ",
            "changing color value to 2 should reveal only one record");

        // Saving the form view should show a readonly domain containing the
        // "color" field
        form.$buttons.find('.o_form_button_save').click();
        $domain = form.$(".o_form_field_domain");
        assert.ok($domain.html().indexOf("Color index") >= 0,
            "field selector readonly value should now contain 'Color index'");
        form.destroy();
    });

    QUnit.test('domain field is correctly reset on every view change', function (assert) {
        assert.expect(7);

        this.data.partner.records[0].foo = '[["id","=",1]]';
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        var form = createView({
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
        form.$buttons.find('.o_form_button_edit').click();

        // As the domain is equal to [["id", "=", 1]] there should be a field
        // selector to change this
        var $domain = form.$(".o_form_field_domain");
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1,
            "there should be a field selector");

        // Focusing its input should open the field selector popover
        $fieldSelector.trigger('focusin');
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
        form.$(".o_field_widget.o_form_input").click().val("partner_type").trigger("input");

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
});
});
});
