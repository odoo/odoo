/** @odoo-module **/

import { getFixture, click, editInput } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

const { DateTime } = luxon;

let target, serverData;

const arch =
    '<tree editable="top" js_class="inventory_report_list">'+
    '<field name="name"/>'+
    '<field name="age"/>'+
    '<field name="job"/>'+
    '<field name="create_date" invisible="1"/>'+
    '<field name="write_date" invisible="1"/>'+
    '</tree>';

const setup_date = DateTime.fromISO('2022-01-03T08:03:44+00:00').toSQL();

function mockRPC(route, args) {
    if (route === '/web/dataset/call_kw/person/create') {
        // simulate 'stock.quant' create function which can return existing record
        args.args[0].create_date = DateTime.now().toSQL();
        args.args[0].write_date = args.args[0].create_date;
        var name = args.args[0].name;
        var age = args.args[0].age;
        var job = args.args[0].job;
        for (var d of serverData.models.person.records) {
            if (d.name === name) {
                d.age = age;
                d.job = job;
                d.write_date = args.args[0].write_date;
                return Promise.resolve(d.id);
            }
        }
    }
}

QUnit.module(
    "Views",
    {
        beforeEach() {
            target = getFixture();
            serverData = {
                models: {
                    person: {
                        fields: {
                            name: {string: "Name", type: "char"},
                            age: {string: "Age", type: "integer"},
                            job: {string: "Profession", type: "char"},
                            // standard fields
                            create_date: {string: "Created on", type: "datetime" },
                            write_date: {string: "Last Updated on", type: "datetime" },
                        },
                        records: [
                            {id: 1, name: 'Daniel Fortesque', age: 32, job: 'Soldier', create_date: setup_date, write_date: setup_date},
                            {id: 2, name: 'Samuel Oak', age: 64, job: 'Professor', create_date: setup_date, write_date: setup_date},
                            {id: 3, name: 'Leto II Atreides', age: 128, job: 'Emperor', create_date: setup_date, write_date: setup_date},
                        ]
                    },
                },
            };
            setupViewRegistries();
        },
    },
    function () {

    QUnit.module("InventoryReportListView");

    QUnit.test('Create new record correctly', async function (assert) {

        assert.expect(2);

        await makeView({
            type: 'list',
            resModel: 'person',
            serverData,
            arch: arch,
            mockRPC: mockRPC,
            context: {
                inventory_mode: true,
            },
        });

        // Check we have initially 3 records
        assert.containsN(target, '.o_data_row', 3, "should have 3 records");

        // Create a new line...
        await click(target.querySelector(".o_list_button_add"));
        await editInput(target, "[name=name] input", 'Bilou');
        await editInput(target, "[name=age] input", '24');
        await click(target.querySelector(".o_list_button_save"));

        // Check new record is in the list
        assert.containsN(target, '.o_data_row', 4, "should now have 4 records");
    });

    QUnit.test('Don\'t duplicate record', async function (assert) {

        assert.expect(3);

        await makeView({
            type: 'list',
            resModel: 'person',
            serverData,
            arch: arch,
            mockRPC: mockRPC,
            context: {
                inventory_mode: true,
            },
        });

        // Check we have initially 3 records
        assert.containsN(target, '.o_data_row', 3, "should have 3 records");

        // Create a new line for an existing record...
        let name = serverData.models.person.records[2].name, age = '72';
        await click(target.querySelector(".o_list_button_add"));
        await editInput(target, "[name=name] input", name);
        await editInput(target, "[name=age] input", age);
        await click(target.querySelector(".o_list_button_save"));

        // Check we still have 3 records...
        assert.containsN(target, '.o_data_row', 3, "should still have 3 records");
        // ... and verify update has occurred.
        var nameField =$(target).find('td[data-tooltip="' + name + '"]');
        var ageField = nameField.parent().find('.o_list_number');
        assert.strictEqual(ageField.text(), age, "The age field must be updated");
    });

    QUnit.test('Work in grouped list', async function (assert) {

        assert.expect(6);

        await makeView({
            type: "list",
            resModel: 'person',
            serverData,
            arch: arch,
            mockRPC: mockRPC,
            context: {
                inventory_mode: true,
            },
            groupBy: ['job'], // Groups are Emperor, Professor, Soldier
        });

        // Open 'Professor' group
        await click(target.querySelectorAll(".o_group_header")[1]);

        // Check we have only 1 record...
        assert.containsN(target, '.o_data_row', 1, "should have 1 record");

        // Create a new record...
        let name = 'Del Tutorial', age = "32";
        await click(target, ".o_group_field_row_add a");
        await editInput(target, "[name=name] input", name);
        await editInput(target, "[name=age] input", age);
        await click(target.querySelector(".o_list_button_save"));
        // Check we have 2 records...
        assert.containsN(target, '.o_data_row', 2, "should have 2 records");

        // Create an existing record...
        name = serverData.models.person.records[1].name;
        age = "55";
        await click(target, ".o_group_field_row_add a");
        await editInput(target, "[name=name] input", name);
        await editInput(target, "[name=age] input", age);
        await click(target.querySelector(".o_list_button_save"));
        // Check we still have 2 records...
        assert.containsN(target, '.o_data_row', 2, "should still have 2 records");

        // Create an existing but not displayed record...
        name = serverData.models.person.records[0].name;
        await click(target, ".o_group_field_row_add a");
        await editInput(target, "[name=name] input", name);
        await editInput(target, "[name=age] input", age);
        await editInput(target, "[name=job] input", "Soldier"); // let it in its original group
        await click(target.querySelector(".o_list_button_save"));
        // Check we have 3 records...
        assert.containsN(target, '.o_data_row', 3, "should have 3 records");

        // Opens 'Soldier' group
        await click(target.querySelectorAll(".o_group_header")[2]);
        let rows = target.querySelectorAll(".o_data_row");

        // Check 'original' record has been updated...
        // : Daniel Fortesque is in record 0 for group Soldier and in record 3 for group Professor
        assert.strictEqual(rows[0].querySelector('[name="age"]').textContent, age, "age of the record must be updated");

        // Edit the freshly created record...
        await click(rows[3].querySelector(".o_field_cell"));
        await editInput(target, "[name=age] input", "66");
        await click(target, ".o_list_view");

        // Check both records have been updated...
        assert.strictEqual(rows[0].querySelector('[name="age"]').textContent, rows[3].querySelector('[name="age"]').textContent, "age of the record must be updated");
    });
    }
);
