odoo.define('web.singleton_list_tests', function (require) {
"use strict";

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
                    job: {string: "Profession", type: "char"},
                },
                records: [
                    {id: 1, name: 'Daniel Fortesque', age: 32, job: 'Soldier'},
                    {id: 2, name: 'Samuel Oak', age: 64, job: 'Professor'},
                    {id: 3, name: 'Leto II Atreides', age: 128, job: 'Emperor'},
                ]
            },
        };
        this.mockRPC = function (route, args) {
            if (route === '/web/dataset/call_kw/person/create') {
                var name = args.args[0].name;
                var age = args.args[0].age;
                var job = args.args[0].job;
                for (var d of this.data.person.records) {
                    if (d.name === name) {
                        d.age = age;
                        d.job = job;
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
        var name = 'Samuel Oak';
        await testUtils.fields.editInput($input, name);
        await testUtils.fields.triggerKeydown($input, 'tab');

        $input = $('.o_selected_row input[name=age]');
        var age = '72';
        await testUtils.fields.editInput($input, age);
        await testUtils.fields.triggerKeydown($input, 'enter');

        // Checks we have still only 3 records...
        assert.containsN(list, '.o_data_row', 3, "should still have 3 records");
        // ... and verify modification was occurred.
        var nameField = list.$('td[title="' + name + '"]');
        var ageField = nameField.parent().find('.o_list_number');
        assert.strictEqual(ageField.text(), age, "The age field must be updated");
        list.destroy();
    });

    QUnit.test('Don\'t raise error when trying to create duplicate line', async function (assert) {
        assert.expect(3);
       /* In some condition, a list editable with the `singletonlist` js_class
       can try to select a record at a line who isn't the same place anymore.
       In this case, the list can try to find the id of an undefined record.
       This test just insures we don't raise a traceback in this case.
       */
        var list = await createView({
            View: SingletonListView,
            model: 'person',
            data: {
                person: {
                    fields: {
                        name: {string: "Name", type: "char"},
                        age: {string: "Age", type: "integer"},
                    },
                    records: [
                        {id: 1, name: 'Bobby B. Bop', age: 18},
                    ]
                }
            },
            arch: '<tree editable="top" js_class="singleton_list">'+
                    '<field name="name"/>'+
                    '<field name="age"/>'+
                   '</tree>',
            mockRPC: this.mockRPC,
        });
        // Checks we have initially 1 record
        assert.containsN(list, '.o_data_row', 1, "should have 1 records");

        // Creates a new line...
        await testUtils.dom.click($('.o_list_button_add'));
        // ... and fills fields with already existing value
        var $input = $('.o_selected_row input[name=name]');
        var name = 'Bobby B. Bop';
        await testUtils.fields.editInput($input, name);
        await testUtils.fields.triggerKeydown($input, 'tab');

        $input = $('.o_selected_row input[name=age]');
        var age = '22';
        await testUtils.fields.editInput($input, age);
        // This operation causes list'll try to select undefined record.
        await testUtils.fields.triggerKeydown($input, 'enter');

        // Checks we have still only 1 record...
        assert.containsN(list, '.o_data_row', 1, "should now have 1 records");
        // ... and verify modification was occurred.
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
        await testUtils.fields.editInput($input, 'Leto II Atreides');
        await testUtils.fields.triggerKeydown($input, 'tab');
        $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '800');
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

    QUnit.test('Work in grouped list', async function (assert) {
        assert.expect(6);

        var refresh_count = 0;
        var list = await createView({
            View: SingletonListView,
            model: 'person',
            data: this.data,
            arch: '<tree editable="top" js_class="singleton_list">'+
                    '<field name="name"/>'+
                    '<field name="age"/>'+
                    '<field name="job"/>'+
                   '</tree>',
            mockRPC: this.mockRPC,
            groupBy: ['job'],
        });
        list.realReload = list.reload;
        list.reload = function () {
            refresh_count++;
            return this.realReload();
        };
        // Opens 'Professor' group
        await testUtils.dom.click(list.$('.o_group_header:nth-child(2)'));

        // Creates a new record...
        await testUtils.dom.click(list.$('.o_add_record_row a'));
        var $input = $('.o_selected_row input[name=name]');
        await testUtils.fields.editInput($input, 'Del Tutorial');
        await testUtils.fields.triggerKeydown($input, 'tab');
        $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '32');
        await testUtils.fields.triggerKeydown($input, 'tab');
        await testUtils.dom.click($('.o_list_button_save'));
        // ... then checks the list didn't refresh
        assert.strictEqual(refresh_count, 0,
            "don't refresh when creating new record");

        // Creates an existing record in same group...
        await testUtils.dom.click(list.$('.o_add_record_row a'));
        var $input = $('.o_selected_row input[name=name]');
        await testUtils.fields.editInput($input, 'Samuel Oak');
        await testUtils.dom.click($('.o_list_button_save'));
        // ... then checks the list has been refreshed
        assert.strictEqual(refresh_count, 1,
            "refresh when try to create an existing record");

        // Creates an existing but not displayed record...
        await testUtils.dom.click(list.$('.o_add_record_row a'));
        var $input = $('.o_selected_row input[name=name]');
        await testUtils.fields.editInput($input, 'Daniel Fortesque');
        await testUtils.fields.triggerKeydown($input, 'tab');
        $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '55');
        await testUtils.fields.triggerKeydown($input, 'tab');
        $input = $('.o_selected_row input[name=job]');
        await testUtils.fields.editInput($input, 'Soldier');
        await testUtils.dom.click($('.o_list_button_save'));
        // .. then checks the list didn't refresh
        assert.strictEqual(refresh_count, 1,
            "don't refresh when creating an existing record but this record " +
            "isn't present in the view");

        // Opens 'Soldier' group
        await testUtils.dom.click(list.$('.o_group_header:nth-child(1)').first());
        // Checks the record has been correctly updated
        var ageCell = $('tr.o_data_row td.o_list_number').first();
        assert.strictEqual(ageCell.text(), "55",
            "age of the record must be updated");
        // Edits the freshly created record...
        await testUtils.dom.click(list.$('tr.o_data_row td.o_list_number').eq(1));
        $input = $('.o_selected_row input[name=age]');
        await testUtils.fields.editInput($input, '66');
        await testUtils.dom.click($('.o_list_button_save'));
        // ... then checks the list and data have been refreshed
        assert.strictEqual(refresh_count, 2,
            "refresh when try to create an existing record present in the view");
        ageCell = $('tr.o_data_row td.o_list_number').first();
        assert.strictEqual(ageCell.text(), "66",
            "age of the record must be updated");

        list.destroy();
    });
});

});
