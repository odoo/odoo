odoo.define('web.data_export_tests', function (require) {
"use strict";

var framework = require('web.framework');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('widgets', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                },
                records: [
                    {
                        id: 1,
                        foo: "yop",
                    },
                ]
            },
            'ir.exports': {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: [],
            },
        };
    }
}, function () {

    QUnit.module('Data Export');


    QUnit.test('exporting all data in list view', function (assert) {
        assert.expect(7);

        var blockUI = framework.blockUI;
        var unblockUI = framework.unblockUI;
        framework.blockUI = function () {
            assert.step('block UI');
        };
        framework.unblockUI = function () {
            assert.step('unblock UI');
        };

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                sidebar: true,
            },
            mockRPC: function (route) {
                if (route === '/web/export/formats') {
                    return $.when([
                        {tag: 'csv', label: 'CSV'},
                        {tag: 'xls', label: 'Excel'},
                    ]);
                }
                if (route === '/web/export/get_fields') {
                    return $.when([
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
                            field_type: 'text',
                            id: "note",
                            relation_field: null,
                            required: false,
                            string: 'Description',
                            value: "note",
                        }
                    ]);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: function (params) {
                    assert.step(params.url);
                    params.complete();
                },
            },
        });

        list.getParent().searchview = {
            build_search_data: function () {
                assert.step('build_search_data');
                return {
                    contexts: [],
                    domains: [],
                    groupbys: [],
                };
            },
        };
        list.$('thead th.o_list_record_selector input').click();
        list.sidebar.$('a:contains(Export)').click();

        assert.strictEqual($('.modal').length, 1, "a modal dialog should be open");
        assert.strictEqual($('span.o_tree_column:contains(Activities)').length, 1,
            "the Activities field should be in the list of exportable fields");

        // select the field Description, click on add, then export and close
        $('.modal span:contains(Description)').click();
        $('.modal .o_add_field').click();
        $('.modal span:contains(Export To File)').click();
        $('.modal span:contains(Close)').click();

        list.destroy();
        framework.blockUI = blockUI;
        framework.unblockUI = unblockUI;
        assert.verifySteps([
            'build_search_data',
            'block UI',
            '/web/export/csv',
            'unblock UI',
        ]);
    });

});

});
