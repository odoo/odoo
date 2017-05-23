odoo.define('account.setup_bar_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');

var createView = testUtils.createView;

QUnit.module('Views', {}, function () {

QUnit.module('Account Dashboard Setup Bar', {
    beforeEach: function() {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                },
                records: [
                    {id: 1, foo: "yop"},
                    {id: 2, foo: "blip"},
                    {id: 3, foo: "gnap"},
                    {id: 4, foo: "blip"},
                ]
            },
        };
        this.dashboard_data = {
            show_setup_bar: true,
            company: false,
            bank: false,
            fiscal_year: false,
            chart_of_accounts: false,
            initial_balance: false,
        };
    }
});

QUnit.test('setup bar basic rendering', function(assert) {
    assert.expect(2);

    var dashboard_data = this.dashboard_data;
    var kanban = createView({
        View: view_registry.get('account_setup_bar'),
        model: 'partner',
        data: this.data,
        arch: '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates>' +
              '</kanban>',
        mockRPC: function(route, args) {
            if (args.method === 'retrieve_account_dashboard_setup_bar') {
                assert.ok(true, "should call /retrieve_account_dashboard_setup_bar");
                return $.when(dashboard_data);
            }
            return this._super(route, args);
        },
    });

    assert.strictEqual(kanban.$('.o_account_dashboard_header').length, 1, "should render the setup bar");
    kanban.destroy();
});

});

});
