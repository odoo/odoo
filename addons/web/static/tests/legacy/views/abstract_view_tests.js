odoo.define('web.abstract_view_tests', function (require) {
"use strict";

const { registry } = require('@web/core/registry');
const legacyViewRegistry = require('web.view_registry');
var ListView = require('web.ListView');

const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');

QUnit.module('LegacyViews', {
    beforeEach: function () {
        this.data = {
            fake_model: {
                fields: {},
                record: [],
            },
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                },
                records: [
                    {id: 1, bar: true, foo: "yop"},
                    {id: 2, bar: true, foo: "blip"},
                ]
            },
        };
    },
}, function () {

    QUnit.module('AbstractView');

    QUnit.test('group_by from context can be a string, instead of a list of strings', async function (assert) {
        assert.expect(1);

        registry.category("views").remove("list"); // remove new list from registry
        legacyViewRegistry.add("list", ListView); // add legacy list -> will be wrapped and added to new registry

        const serverData = {
            actions: {
                1: {
                    id: 1,
                    name: 'Foo',
                    res_model: 'foo',
                    type: 'ir.actions.act_window',
                    views: [[false, 'list']],
                    context: {
                        group_by: 'bar',
                    },
                }
            },
            views: {
                'foo,false,list': '<tree><field name="foo"/><field name="bar"/></tree>',
                'foo,false,search': '<search></search>',
            },
            models: this.data
        };

        const mockRPC = (route, args) => {
            if (args.method === 'web_read_group') {
                assert.deepEqual(args.kwargs.groupby, ['bar']);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
    });

});
});
