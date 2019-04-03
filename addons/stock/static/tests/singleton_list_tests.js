odoo.define('web.singleton_list_tests', function (require) {
"use strict";

var core = require('web.core');
var SingletonListView = require('stock.SingletonListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;


QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            person: {
                fields: {
                    name: {string: "Name", type: "char"},
                    age: {string: "Age", type: "integer"},
                },
                records: [
                    {id: 1, name: 'D. Fortesque', age: 32},
                    {id: 2, name: 'P. Oak', age: 64},
                    {id: 3, name: 'Leto II A.', age: 128},
                ]
            },
        };
        this.mockRPC = function (route, args) {
            if (route === '/web/dataset/call_kw/person/create') {
                var name = args.args[0].name;
                var age = args.args[0].age;
                for (var d of this.data.person.records) {
                    if (d.name === name) {
                        d.age = age;
                        return Promise.resolve(d.id);
                    }
                }
            }
            return this._super.apply(this, arguments);
        };
    }
}, function () {

    QUnit.module('SingletonListView');

    QUnit.test('Create new record correctly', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: SingletonListView,
            model: 'person',
            data: this.data,
            arch: '<tree editable="top" js_class="singleton_list">'+
                    '<field name="name"/>'+
                    '<field name="age"/>'+
                   '</tree>',
            mockRPC: this.mockRPC,
        });
        // Checks we have initially 3 records
        assert.containsN(list, '.o_data_row', 3, "should have 3 records");

        // Creates a new line...
        await testUtils.dom.click($('.o_list_button_add'));
        // ... and fills fields with new values
        var $input = $('.o_selected_row input[name=name]');
        await testUtils.fields.editInput($input, 'Bilou');
        await testUtils.fields.triggerKeydown($input, 'tab');

        $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '24');
        await testUtils.fields.triggerKeydown($input, 'enter');
        await testUtils.dom.click($('.o_list_button_save'));

        // Checks new record is in the list
        assert.containsN(list, '.o_data_row', 4, "should now have 4 records");
        list.destroy();
    });

    QUnit.test('Don\'t duplicate record', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: SingletonListView,
            model: 'person',
            data: this.data,
            arch: '<tree editable="top" js_class="singleton_list">'+
                    '<field name="name"/>'+
                    '<field name="age"/>'+
                   '</tree>',
            mockRPC: this.mockRPC,
        });
        // Checks we have initially 3 records
        assert.containsN(list, '.o_data_row', 3, "should have 3 records");

        // Creates a new line...
        await testUtils.dom.click($('.o_list_button_add'));
        // ... and fills fields with already existing value
        var $input = $('.o_selected_row input[name=name]');
        var name = 'P. Oak';
        await testUtils.fields.editInput($input, name);
        await testUtils.fields.triggerKeydown($input, 'tab');

        $input = $('.o_selected_row input[name=age]');
        var age = '72';
        await testUtils.fields.editInput($input, age);
        await testUtils.fields.triggerKeydown($input, 'enter');
        await testUtils.dom.click($('.o_list_button_save'));

        // Checks we have still only 3 records...
        assert.containsN(list, '.o_data_row', 3, "should now have 4 records");
        // ... and verify modification was occured.
        var nameField = list.$('td[title="' + name + '"]');
        var ageField = nameField.parent().find('.o_list_number');
        assert.strictEqual(ageField.text(), age, "The age field must be updated");
        list.destroy();
    });

    QUnit.test('Refresh the list only when needed', async function (assert) {
        assert.expect(3);

        var refresh_count = 0;
        var list = await createView({
            View: SingletonListView,
            model: 'person',
            data: this.data,
            arch: '<tree editable="top" js_class="singleton_list">'+
                    '<field name="name"/>'+
                    '<field name="age"/>'+
                   '</tree>',
            mockRPC: this.mockRPC,
        });
        list.realReload = list.reload;
        list.reload = function () {
            refresh_count++;
            return this.realReload();
        };
        // Modify Record
        await testUtils.dom.click(list.$('.o_data_row:nth-child(2) > .o_list_number'));
        var $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '70');
        await testUtils.fields.triggerKeydown($input, 'enter');
        await testUtils.dom.click($('.o_list_button_save'));
        assert.strictEqual(refresh_count, 0, "don't refresh when edit existing line");

        // Add existing record
        await testUtils.dom.click($('.o_list_button_add'));
        $input = $('.o_selected_row input[name=name]');
        await testUtils.fields.editInput($input, 'Leto II A.');
        await testUtils.fields.triggerKeydown($input, 'tab');
        $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '800');
        await testUtils.fields.triggerKeydown($input, 'enter');
        await testUtils.dom.click($('.o_list_button_save'));
        assert.strictEqual(refresh_count, 1, "refresh after tried to create an existing record");

        // Add new record
        await testUtils.dom.click($('.o_list_button_add'));
        $input = $('.o_selected_row input[name=name]');
        await testUtils.fields.editInput($input, 'Valentin Cognito');
        await testUtils.fields.triggerKeydown($input, 'tab');
        $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '37');
        await testUtils.fields.triggerKeydown($input, 'enter');
        await testUtils.dom.click($('.o_list_button_save'));
        assert.strictEqual(refresh_count, 1, "don't refresh when create entirely new record");

        list.destroy();
    });
});

});
