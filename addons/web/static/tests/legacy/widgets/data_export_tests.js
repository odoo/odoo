odoo.define('web.data_export_tests', function (require) {
"use strict";

const data = require('web.data');
const framework = require('web.framework');
const ListView = require('web.ListView');
const testUtils = require('web.test_utils');

const createView = testUtils.createView;

QUnit.module('widgets', {
    beforeEach: function () {
        this.data = {
            'partner': {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "char"},
                    unexportable: {string: "Unexportable", type: "boolean", exportable: false},
                },
                records: [
                    {
                        id: 1,
                        foo: "yop",
                        bar: "bar-blup",
                    }, {
                        id: 2,
                        foo: "yop",
                        bar: "bar-yop",
                    }, {
                        id: 3,
                        foo: "blup",
                        bar: "bar-blup",
                    }
                ]
            },
            'ir.exports': {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: [],
            },
        };
        this.mockSession = {
            async user_has_group(g) { return g === 'base.group_allow_export'; }
        }
        this.mockDataExportRPCs = function (route) {
            if (route === '/web/export/formats') {
                return Promise.resolve([
                    {tag: 'csv', label: 'CSV'},
                    {tag: 'xls', label: 'Excel'},
                ]);
            }
            if (route === '/web/export/get_fields') {
                return Promise.resolve([
                    {
                        field_type: "one2many",
                        string: "Activities",
                        required: false,
                        value: "activity_ids/id",
                        id: "activity_ids",
                        params: {"model": "mail.activity", "prefix": "activity_ids", "name": "Activities"},
                        relation_field: "res_id",
                        children: true,
                    }, {
                        children: false,
                        field_type: 'char',
                        id: "foo",
                        relation_field: null,
                        required: false,
                        string: 'Foo',
                        value: "foo",
                    }
                ]);
            }
            return this._super.apply(this, arguments);
        };
    }
}, function () {

    QUnit.module('Data Export');


    QUnit.test('exporting all data in list view', async function (assert) {
        assert.expect(8);

        var blockUI = framework.blockUI;
        var unblockUI = framework.unblockUI;
        framework.blockUI = function () {
            assert.step('block UI');
        };
        framework.unblockUI = function () {
            assert.step('unblock UI');
        };

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                hasActionMenus: true,
            },
            mockRPC: this.mockDataExportRPCs,
            session: {
                ...this.mockSession,
                get_file: function (params) {
                    assert.step(params.url);
                    params.complete();
                },
            },
        });


        await testUtils.dom.click(list.$('thead th.o_list_record_selector input'));

        await testUtils.controlPanel.toggleActionMenu(list);
        await testUtils.controlPanel.toggleMenuItem(list, 'Export');

        assert.strictEqual($('.modal').length, 1, "a modal dialog should be open");
        assert.strictEqual($('div.o_tree_column:contains(Activities)').length, 1,
            "the Activities field should be in the list of exportable fields");
        assert.strictEqual($('.modal .o_export_field').length, 1, "There should be only one export field");
        assert.strictEqual($('.modal .o_export_field').data('field_id'), 'foo', "There should be only one export field");

        // select the field Description, click on add, then export and close
        await testUtils.dom.click($('.modal .o_tree_column:contains(Foo) .o_add_field'));
        await testUtils.dom.click($('.modal span:contains(Export)'));
        await testUtils.dom.click($('.modal span:contains(Close)'));
        list.destroy();
        framework.blockUI = blockUI;
        framework.unblockUI = unblockUI;
        assert.verifySteps([
            'block UI',
            '/web/export/csv',
            'unblock UI',
        ]);
    });

    QUnit.test('exporting data in list view (multi pages)', async function (assert) {
        assert.expect(4);

        let expectedData;
        const list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            domain: [['id', '<', 1000]],
            viewOptions: {
                hasActionMenus: true,
            },
            mockRPC: this.mockDataExportRPCs,
            session: {
                ...this.mockSession,
                get_file: function (params) {
                    const data = JSON.parse(params.data.data);
                    assert.deepEqual({ids: data.ids, domain: data.domain}, expectedData);
                    params.complete();
                },
            },
        });

        // select all records (first page) and export
        expectedData = {
            ids: [1, 2],
            domain: [['id', '<', 1000]],
        };
        await testUtils.dom.click(list.$('thead th.o_list_record_selector input'));

        await testUtils.controlPanel.toggleActionMenu(list);
        await testUtils.controlPanel.toggleMenuItem(list, 'Export');

        assert.containsOnce(document.body, '.modal');

        await testUtils.dom.click($('.modal span:contains(Export)'));
        await testUtils.dom.click($('.modal span:contains(Close)'));

        // select all domain and export
        expectedData = {
            ids: false,
            domain: [['id', '<', 1000]],
        };
        await testUtils.dom.click(list.$('.o_list_selection_box .o_list_select_domain'));

        await testUtils.controlPanel.toggleActionMenu(list);
        await testUtils.controlPanel.toggleMenuItem(list, 'Export');

        assert.containsOnce(document.body, '.modal');

        await testUtils.dom.click($('.modal span:contains(Export)'));
        await testUtils.dom.click($('.modal span:contains(Close)'));

        list.destroy();
    });

    QUnit.test('exporting view with non-exportable field', async function (assert) {
        assert.expect(0);

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree><field name="unexportable"/></tree>',
            viewOptions: {
                hasActionMenus: true,
            },
            mockRPC: this.mockDataExportRPCs,
            session: {
                ...this.mockSession,
                get_file: function (params) {
                    assert.step(params.url);
                    params.complete();
                },
            },
        });

        await testUtils.dom.click(list.$('thead th.o_list_record_selector input'));

        await testUtils.controlPanel.toggleActionMenu(list);
        await testUtils.controlPanel.toggleMenuItem(list, 'Export');

        list.destroy();
    });

    QUnit.test('saving fields list when exporting data', async function (assert) {
        assert.expect(4);

        var create = data.DataSet.prototype.create;

        data.DataSet.prototype.create = function () {
            assert.step('create');
            return Promise.resolve([]);
        };

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                hasActionMenus: true,
            },
            session: this.mockSession,
            mockRPC: this.mockDataExportRPCs,
        });


        // Open the export modal
        await testUtils.dom.click(list.$('thead th.o_list_record_selector input'));
        await testUtils.controlPanel.toggleActionMenu(list);
        await testUtils.controlPanel.toggleMenuItem(list, 'Export');

        assert.strictEqual($('.modal').length, 1,
            "a modal dialog should be open");

        // Select 'Activities' in fields to export
        await testUtils.dom.click($('.modal .o_export_tree_item:contains(Activities) .o_add_field'));
        assert.strictEqual($('.modal .o_fields_list .o_export_field').length, 2,
            "there should be two items in the fields list");
        // Save as template
        await testUtils.fields.editAndTrigger($('.modal .o_exported_lists_select'), 'new_template', ['change']);
        await testUtils.fields.editInput($('.modal .o_save_list .o_save_list_name'), 'fields list');
        await testUtils.dom.click($('.modal .o_save_list .o_save_list_btn'));

        assert.verifySteps(['create'],
            "create should have been called");

        // Close the modal and destroy list
        await testUtils.dom.click($('.modal button span:contains(Close)'));
        list.destroy();

        // restore create function
        data.DataSet.prototype.create = create;
    });

    QUnit.test('Export dialog UI test', async function (assert) {
        assert.expect(5);
        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                hasActionMenus: true,
            },
            session: this.mockSession,
            mockRPC: this.mockDataExportRPCs,
        });


        // Open the export modal
        await testUtils.dom.click(list.$('thead th.o_list_record_selector input'));
        await testUtils.controlPanel.toggleActionMenu(list);
        await testUtils.controlPanel.toggleMenuItem(list, 'Export');

        assert.strictEqual($('.modal .o_export_tree_item:visible').length, 2, "There should be only two items visible");
        await testUtils.dom.click($('.modal .o_export_search_input'));
        $('.modal .o_export_search_input').val('Activities').trigger($.Event('input', {
            keyCode: 65,
        }));
        assert.strictEqual($('.modal .o_export_tree_item:visible').length, 1, "Only match item visible");
        // Add field
        await testUtils.dom.click($('.modal div:contains(Activities) .o_add_field'));
        assert.strictEqual($('.modal .o_fields_list li').length, 2, "There should be two fields in export field list.");
        assert.strictEqual($('.modal .o_fields_list li:eq(1)').text(), "Activities",
            "string of second field in export list should be 'Activities'");
        // Remove field
        await testUtils.dom.click($('.modal .o_fields_list li:first .o_remove_field'));
        assert.strictEqual($('.modal .o_fields_list li').length, 1, "There should be only one field in list");
        list.destroy();
    });

    QUnit.test('Direct export button invisible', async function (assert) {
        assert.expect(1)

        let list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: `<tree export_xlsx="0"><field name="foo"/></tree>`,
            session: this.mockSession,
        });
        assert.containsNone(list, '.o_list_export_xlsx')
        list.destroy();
    });

    QUnit.test('Direct export list ', async function (assert) {
        assert.expect(2);

        let list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: `
                <tree export_xlsx="1">
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            domain: [['bar', '!=', 'glou']],
            session: {
                ...this.mockSession,
                get_file(args) {
                    let data = JSON.parse(args.data.data);
                    assert.strictEqual(args.url, '/web/export/xlsx', "should call get_file with the correct url");
                    assert.deepEqual(data, {
                        context: {},
                        model: 'partner',
                        domain: [['bar', '!=', 'glou']],
                        groupby: [],
                        ids: false,
                        import_compat: false,
                        fields: [{
                            name: 'foo',
                            label: 'Foo',
                            type: 'char',
                        }, {
                            name: 'bar',
                            label: 'Bar',
                            type: 'char',
                        }]
                    }, "should be called with correct params");
                    args.complete();
                },
            },
        });

        // Download
        await testUtils.dom.click(list.$buttons.find('.o_list_export_xlsx'));

        list.destroy();
    });

    QUnit.test('Direct export grouped list ', async function (assert) {
        assert.expect(2);

        let list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            groupBy: ['foo', 'bar'],
            domain: [['bar', '!=', 'glou']],
            session: {
                ...this.mockSession,
                get_file(args) {
                    let data = JSON.parse(args.data.data);
                    assert.strictEqual(args.url, '/web/export/xlsx', "should call get_file with the correct url");
                    assert.deepEqual(data, {
                        context: {},
                        model: 'partner',
                        domain: [['bar', '!=', 'glou']],
                        groupby: ['foo', 'bar'],
                        ids: false,
                        import_compat: false,
                        fields: [{
                            name: 'foo',
                            label: 'Foo',
                            type: 'char',
                        }, {
                            name: 'bar',
                            label: 'Bar',
                            type: 'char',
                        }]
                    }, "should be called with correct params");
                    args.complete();
                },
            },
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_export_xlsx'));

        list.destroy();
    });
});

});
