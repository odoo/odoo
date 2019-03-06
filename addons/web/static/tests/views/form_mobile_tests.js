odoo.define('web.form_mobile_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    bar: {string: "Bar", type: "boolean"},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    bar: true,
                    foo: "yop",
                }, {
                    id: 2,
                    display_name: "second record",
                    bar: true,
                    foo: "blip",
                }, {
                    id: 4,
                    display_name: "aaa",
                    state: "ef",
                }, {
                    id: 5,
                    display_name: "aaa",
                    foo:'',
                    bar: false,
                }],
                onchanges: {},
            },
        };
    }
}, function () {

    QUnit.module('FormView');

    QUnit.test('switching to next/previous record on swipe in readonly mode', function (assert) {
        assert.expect(6);

        // mimic touchSwipe library's swipe method
        var oldSwipe = $.fn.swipe;
        var swipeLeft, swipeRight;
        $.fn.swipe = function (params) {
            swipeLeft = params.swipeLeft.bind(this);
            swipeRight = params.swipeRight.bind(this);
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/read') {
                    assert.step(args.args[0][0]);
                }
                return this._super(route, args);
            },
        });

        swipeLeft();
        assert.strictEqual(form.pager.$('.o_pager_value').text(), '2', 'pager value should be 2');

        swipeRight();
        assert.strictEqual(form.pager.$('.o_pager_value').text(), '1', 'pager value should be 1');

        assert.verifySteps([1, 2, 1]);

        $.fn.swipe = oldSwipe;
        form.destroy();
    });
});

});
