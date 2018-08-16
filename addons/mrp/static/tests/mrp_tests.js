odoo.define('mrp.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require("web.test_utils");

var createView = testUtils.createView;

QUnit.module('mrp', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    state: {
                        string: "State",
                        type: "selection",
                        selection: [['waiting', 'Waiting'], ['chilling', 'Chilling']],
                    },
                    duration: {string: "Duration", type: "float"},
                },
                records: [{
                    id: 1,
                    state: 'waiting',
                    duration: 6000,
                }],
                onchanges: {},
            },
        };
    },
}, function () {

    QUnit.test("bullet_state: basic rendering", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            res_id: 1,
            arch:
                '<form>' +
                    '<field name="state" widget="bullet_state" options="{\'classes\': {\'waiting\': \'danger\'}}"/>' +
                '</form>',
        });

        assert.strictEqual(form.$('.o_field_widget').text(), "Waiting Materials",
            "the widget should be correctly named");
        assert.strictEqual(form.$('.o_field_widget .badge-danger').length, 1,
            "the badge should be danger");

        form.destroy();
    });

    QUnit.test("mrp_time_counter: basic rendering", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            res_id: 1,
            arch:
                '<form>' +
                    '<field name="duration" widget="mrp_time_counter"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'mrp.workcenter.productivity') {
                    assert.ok(true, "the widget should fetch the mrp.workcenter.productivity");
                    return $.when([{
                        date_start: '2017-01-01 08:00:00',
                        date_end: '2017-01-01 10:00:00',
                    }, {
                        date_start: '2017-01-01 12:00:00',
                        date_end: '2017-01-01 12:30:00',
                    }]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name="duration"]').text(), "02:30:00",
            "the timer should be correctly set");

        form.destroy();
    });
});
});
