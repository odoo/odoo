odoo.define('web.basic_fields_mobile_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
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
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", searchable: true, trim: true},
                    bar: {string: "Bar", type: "boolean", default: true, searchable: true},
                    int_field: {string: "int_field", type: "integer", sortable: true, searchable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1], searchable: true},
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
                }, {
                    id: 2,
                    display_name: "second record",
                    bar: true,
                    foo: "blip",
                    int_field: 0,
                    qux: 0,
                }, {
                    id: 4,
                    display_name: "aaa",
                    foo: "abc",
                    int_field: false,
                    qux: false,
                }],
                onchanges: {},
            },
        };
    }
}, function () {

    QUnit.module('PhoneWidget');

    QUnit.test('phone field in form view on extra small screens', async function (assert) {
        assert.expect(7);

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
        });

        var $phoneLink = form.$('a.o_form_uri.o_field_widget');
        assert.strictEqual($phoneLink.length, 1,
            "should have a anchor with correct classes");
        assert.strictEqual($phoneLink.text(), 'yop',
            "value should be displayed properly");
        assert.hasAttrValue($phoneLink, 'href', 'tel:yop',
            "should have proper tel prefix");

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, 'input[type="text"].o_field_widget',
            "should have an int for the phone field");
        assert.strictEqual(form.$('input[type="text"].o_field_widget').val(), 'yop',
            "input should contain field value in edit mode");

        // change value in edit mode
        await testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), 'new');

        // save
        await testUtils.form.clickSave(form);
        $phoneLink = form.$('a.o_form_uri.o_field_widget');
        assert.strictEqual($phoneLink.text(), 'new',
            "new value should be displayed properly");
        assert.hasAttrValue($phoneLink, 'href', 'tel:new',
            "should still have proper tel prefix");

        form.destroy();
    });

    QUnit.test('phone field in editable list view on extra small screens', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
        });

        assert.containsN(list, '.o_data_row', 3,
            "should have 3 record");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) a').first().text(), 'yop',
            "value should be displayed properly");

        var $phoneLink = list.$('a.o_form_uri.o_field_widget');
        assert.strictEqual($phoneLink.length, 3,
            "should have anchors with correct classes");
        assert.hasAttrValue($phoneLink.first(), 'href', 'tel:yop',
            "should have proper tel prefix");

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
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector) a').first().text(), 'new',
            "value should be properly updated");
        $phoneLink = list.$('a.o_form_uri.o_field_widget');
        assert.strictEqual($phoneLink.length, 3,
            "should still have anchors with correct classes");
        assert.hasAttrValue($phoneLink.first(), 'href', 'tel:new',
            "should still have proper tel prefix");

        list.destroy();
    });

    QUnit.test('phone field does not allow html injections', async function (assert) {
        assert.expect(1);

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
            viewOptions: {
                mode: 'edit',
            },
        });

        var val = '<script>throw Error();</script><script>throw Error();</script>';
        await testUtils.fields.editInput(form.$('input.o_field_widget[name="foo"]'), val);

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$('.o_field_widget').text(), val,
            "value should have been correctly escaped");

        form.destroy();
    });
});
});
});
