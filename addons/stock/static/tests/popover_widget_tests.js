odoo.define('stock.popover_widget_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var FormView = require('web.FormView');
var createView = testUtils.createView;

QUnit.module('widgets', {}, function () {
QUnit.module('ModelFieldSelector', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    json_data: {string: " ", type: "char"},
                },
                records: [
                    {id:1, json_data:'{"color": "text-danger", "msg": "var that = self // why not?", "title": "JS Master"}'}
                ]
            }
        };
    },
}, function () {
    QUnit.test("Test creation/usage popover widget form", async function (assert) {
        assert.expect(6);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="json_data" widget="popover_widget"/>' +
                '</form>',
            res_id: 1
        });

        var $popover = $('div.popover');
        assert.strictEqual($popover.length, 0, "Shouldn't have a popover container in DOM");

        var $popoverButton = form.$('a.fa.fa-info-circle.text-danger');
        assert.strictEqual($popoverButton.length, 1, "Should have a popover icon/button in red");
        assert.strictEqual($popoverButton.prop('special_click'), true, "Special click properpy should be activated");
        await testUtils.dom.triggerEvents($popoverButton, ['focus']);
        $popover = $('div.popover');
        assert.strictEqual($popover.length, 1, "Should have a popover container in DOM");
        assert.strictEqual($popover.html().includes("var that = self // why not?"), true, "The message should be in DOM");
        assert.strictEqual($popover.html().includes("JS Master"), true, "The title should be in DOM");

        form.destroy();
    });
});
});

});
