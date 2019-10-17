odoo.define('sale_timesheet.timesheet_plan_tests', function (require) {
"use strict";

var ProjectPlan = require('sale_timesheet.ProjectPlan');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

function createPlan(params) {
    var Parent = Widget.extend({
        do_push_state: function () {},
    });
    var parent = new Parent();
    testUtils.addMockEnvironment(parent, params);
    var plan = new ProjectPlan(parent, params.action);
    var selector = params.debug ? 'body' : '#qunit-fixture';
    plan.appendTo($(selector));

    plan.destroy = function () {
        delete plan.destroy;
        parent.destroy();
    };

    return plan;
}

QUnit.module('Timesheet Plan', {
    beforeEach: function () {
        this.data = {
            'project.project': {
                fields: {
                    account_id: {string: "Analytic account", type: "many2one", relation: "account.analytic.account"},
                },
                records: []
            },
        };
    }
}, function () {

    QUnit.test('basic timesheet plan rendering', function (assert) {
        assert.expect(5);

        var plan = createPlan({
            archs: {
                'project.project,false,search': '<search></search>',
            },
            data: this.data,
            action: {},
            mockRPC: function (route) {
                assert.step(route);
                if (route === '/timesheet/plan') {
                    return $.when({html_content: '<p>Banach-Tarski</p>'});
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                search: function () {
                    // when the search event get up to the action manager,
                    // bad things can happen
                    throw new Error('Search event should not get out of client action');
                },
            },
        });
        assert.verifySteps([
            "/web/dataset/call_kw/project.project",
            "/timesheet/plan"
        ]);
        assert.strictEqual(plan.$el.text(), 'Banach-Tarski', 'should have rendered html content');
        assert.strictEqual(plan.get('title'), 'Overview',
            'default title should be set');
        plan.destroy();
    });

    QUnit.test('timesheet action takes action name into account', function (assert) {
        assert.expect(1);

        var plan = createPlan({
            archs: {
                'project.project,false,search': '<search></search>',
            },
            data: this.data,
            action: {name: 'Fibonacci'},
            mockRPC: function (route) {
                if (route === '/timesheet/plan') {
                    return $.when({html_content: '<p>Banach-Tarski</p>'});
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(plan.get('title'), 'Fibonacci',
            'title should be set from the action name');
        plan.destroy();
    });
});
});
