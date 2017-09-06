odoo.define('web.upgrade_fields_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('upgrade_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    bar: {string: "Bar", type: "boolean"},
                },
            }
        };
    },
}, function () {

    QUnit.module('UpgradeBoolean');

    QUnit.test('widget upgrade_boolean in a form view', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="bar" widget="upgrade_boolean"/></form>',
        });

        form.$('input:checkbox').click();
        assert.strictEqual($('.modal').length, 1,
            "the 'Upgrade to Enterprise' dialog should be opened");

        form.destroy();
    });

});
});
});
