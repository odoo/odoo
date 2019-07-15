odoo.define('account.grouped_tree_export_as_xlsx', function (require) {
"use strict";

var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;
var session = require('web.session');

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    date: {string: "Some Date", type: "date"}
                },
                records: [
                    { id: 1, bar: true, foo: "yop", date: "2019-01-25" },
                    { id: 2, bar: true, foo: "blip", date: false },
                    { id: 3, bar: true, foo: "gnap", date: "2019-04-26" },
                    { id: 4, bar: false, foo: "blip", date: "2019-07-24" }
                ]
            }
        };
    }
}, function () {
    QUnit.test('grouped list export as xlsx', async function (assert) {
        assert.expect(7);

        // save the session function
        var oldGetFile = session.get_file;
        session.get_file = function (option) {
            var data = JSON.parse(option.data.data);

            assert.deepEqual(data.columns, ['foo', 'bar', 'date'],
                "columns sequence must be foo,bar,date");

            var unFoldedRows = _.filter(data.rows, function(row) {
                return row.type == "list" && row.data.length == 0;
            });
            var foldedRows = _.filter(data.rows, function(row) {
                return row.type == "list" && row.data.length != 0;
            });

            assert.strictEqual(data.rows.length, 3, "there are total three rows");
            assert.strictEqual(unFoldedRows.length, 2, "there are only two rows as grouped with no child record to each.");
            assert.strictEqual(foldedRows.length, 1, "there are only one row with child records");

            if (option.url == "/web/export_xlsx/export") {
                assert.step("export_xlsx_rpc_call");
            }
            option.complete();
            return Promise.resolve();
        };

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree class="account_export_as_xlsx">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="date"/>' +
                  '</tree>',
            groupBy: ['foo']
        });

        // Opening first grouped list
        await testUtils.dom.click(list.$(".o_group_header:eq(0)"));
        assert.containsOnce(list, '.o_control_panel button.o_export_xslx', 'should have export button on control panel');
        await testUtils.dom.click(list.$(".o_control_panel button.o_export_xslx"));
        assert.verifySteps(['export_xlsx_rpc_call'], "export grouped tree with data rpc called");
        list.destroy();
        // restore the session function
        session.get_file = oldGetFile;
    });
});
});
