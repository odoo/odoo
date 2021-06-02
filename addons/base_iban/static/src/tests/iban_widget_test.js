odoo.define('base_iban.iban_widget_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    acc_number: {string: "acc_number", type: "char"},
                },
                records: [{
                    id: 1,
                    acc_number: "",
                }]
            },
        };
        // patch _.debounce to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        _.debounce = _.identity;
    },
    afterEach: function () {
        // unpatch _.debounce
        _.debounce = this.underscoreDebounce;
    }
}, function () {

    QUnit.module('IbanWidget');

    QUnit.test('Iban widgets are correctly rendered', async function (assert) {
        assert.expect(6);
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><sheet><field name="acc_number" widget="iban"/></sheet></form>',
            mockRPC: function (route, args) {
                if (args.method === 'check_iban') {
                    console.log(args.args[1] === "BE00 0000 0000 0000 0000")
                    return Promise.resolve(args.args[1] === "BE00 0000 0000 0000 0000");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.fields.editAndTrigger(form.$('.o_field_widget'), "BE00", 'input');
        assert.containsOnce(form, '.o_iban_fail', "Should be a False account, it's too short");
        assert.containsOnce(form, '.fa-times', "Should have a cross pictogram");

        await testUtils.fields.editAndTrigger(form.$('.o_field_widget'), "BE00 0000 0000 0000 0000", 'input');
        assert.containsOnce(form, '.text-success', "Should have text-success");
        assert.containsOnce(form, '.fa-check', "Should have a valid pictogram");

        await testUtils.fields.editAndTrigger(form.$('.o_field_widget'), "BE00 xxxx xxxx xxxx xxxx", 'input');
        assert.containsOnce(form, '.o_iban_fail', "Should be False account");
        assert.containsOnce(form, '.fa-times', "Should have a cross pictogram");

        form.destroy();
    });
});
});
