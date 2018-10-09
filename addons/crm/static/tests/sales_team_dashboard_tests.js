odoo.define('crm.dashboard_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');

var createView = testUtils.createView;

QUnit.module('CRM Sales Team Dashboard', {
    beforeEach: function () {
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
            nb_opportunities: 6,
            currency_id: 3,
            won: {this_month: 0, last_month: 0, target: 0},
            done: {this_month: 0, last_month: 0, target: 0},
            activity: {next_7_days: 3, today: 1, overdue: 1},
            closing: {next_7_days: 1, today: 0, overdue: 0},
            meeting: {next_7_days: 1, today: 0},
            invoiced: {this_month: 0, last_month: 0, target: 0}
        };
    }
});

QUnit.test('dashboard basic rendering', function (assert) {
    assert.expect(2);

    var dashboard_data = this.dashboard_data;
    var kanban = createView({
        View: view_registry.get('sales_team_dashboard'),
        model: 'partner',
        data: this.data,
        arch: '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates>' +
              '</kanban>',
        mockRPC: function (route, args) {
            if (args.method === 'retrieve_sales_dashboard') {
                assert.ok(true, "should call /retrieve_sales_dashboard");
                return $.when(dashboard_data);
            }
            return this._super(route, args);
        },
    });

    assert.ok(kanban.$('div.o_sales_dashboard').length,
            "should render the dashboard");
});

QUnit.test('dashboard set a new target', function (assert) {
    assert.expect(4);

    var dashboard_data = this.dashboard_data;
    var kanban = createView({
        View: view_registry.get('sales_team_dashboard'),
        model: 'partner',
        data: this.data,
        arch: '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates>' +
              '</kanban>',
        mockRPC: function (route, args) {
            if (args.method === 'retrieve_sales_dashboard') {
                // should be called twice: for the first rendering, and after the target update
                assert.ok(true, "should call /retrieve_sales_dashboard");
                return $.when(dashboard_data);
            }
            if (args.method === 'modify_target_sales_dashboard') {
                assert.ok(true, "should call /modify_target_sales_dashboard");
                dashboard_data[args.args[0]].target = args.args[1];
                return $.when();
            }
            return this._super(route, args);
        },
    });

    kanban.$('.o_target_to_set').first().click(); // click on the target to set
    kanban.$('.o_sales_dashboard input')
        .val('20000')
        .trigger($.Event('keyup', {which: $.ui.keyCode.ENTER})); // set the target

    assert.ok(kanban.$('.o_target_to_set:first():contains(20000)').length,
        "dashboard should have been correctly re-rendered after target update");
});

QUnit.test('dashboard: click on a button to execute an action', function (assert) {
    assert.expect(2);

    var dashboard_data = this.dashboard_data;
    var kanban = createView({
        View: view_registry.get('sales_team_dashboard'),
        model: 'partner',
        data: this.data,
        arch: '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<button name="func_name" String="A" type="object" class="my_button"/>' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</t></templates>' +
              '</kanban>',
        mockRPC: function (route, args) {
            if (args.method === 'retrieve_sales_dashboard') {
                return $.when(dashboard_data);
            }
            return this._super(route, args);
        },
    });


    testUtils.intercept(kanban, 'execute_action', function (event) {
        assert.strictEqual(event.data.action_data.name, 'func_name',
            'execute_action should have been triggered with the correct data');
        assert.strictEqual(event.data.action_data.type, 'object',
            'execute_action should have been triggered with the correct data');
    });

    kanban.$('.my_button:first()').click(); // click on the button of the first card
    kanban.destroy();
});

QUnit.test('dashboard should be displayed even if there is no content', function (assert) {
    assert.expect(2);

    var dashboardData = this.dashboard_data;
    var kanban = createView({
        View: view_registry.get('sales_team_dashboard'),
        model: 'partner',
        data: this.data,
        arch: '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates>' +
              '</kanban>',
        domain: [['id', '=', 239]], // no record will match this domain
        mockRPC: function (route, args) {
            if (args.method === 'retrieve_sales_dashboard') {
                return $.when(dashboardData);
            }
            return this._super(route, args);
        },
        viewOptions: {
            action: {
                help: '<p>A help message</p>',
            },
        },
    });

    assert.strictEqual(kanban.$('div.o_sales_dashboard').length, 1,
        "should render the dashboard");
    assert.strictEqual(kanban.$('.o_view_nocontent:contains(A help message)').length, 1,
        "should correctly render the nocontent helper");

    kanban.destroy();
});

});
