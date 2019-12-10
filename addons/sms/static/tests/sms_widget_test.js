odoo.define('sms.sms_widget_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    message: {string: "message", type: "text"},
                },
                records: [{
                    id: 1,
                    message: "",
                }]
            },
        };
    }
}, function () {

    QUnit.module('SmsWidget');

    QUnit.test('Sms widgets are correctly rendered', async function (assert) {
        assert.expect(9);
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><sheet><field name="message" widget="sms_widget"/></sheet></form>',
        });
        assert.containsOnce(form, '.o_sms_count', "Should have a sms counter");
        assert.strictEqual(form.$('.o_sms_count').text(), '0 characters, fits in 0 SMS (GSM7) ',
            'Should be "0 characters, fits in 0 SMS (GSM7) " by default');
        // GSM-7
        await testUtils.fields.editAndTrigger(form.$('.o_input'), "Hello from Odoo", 'input');
        assert.strictEqual(form.$('.o_sms_count').text(), '15 characters, fits in 1 SMS (GSM7) ',
            'Should be "15 characters, fits in 1 SMS (GSM7) " for "Hello from Odoo"');
        // GSM-7 with \n => this one count as 2 characters
        form.$('.o_input').val("Hello from Odoo\n").trigger('input');
        assert.strictEqual(form.$('.o_sms_count').text(), '17 characters, fits in 1 SMS (GSM7) ',
            'Should be "17 characters, fits in 1 SMS (GSM7) " for "Hello from Odoo\\n"');
        // Unicode => ê
        form.$('.o_input').val("Hêllo from Odoo").trigger('input');
        assert.strictEqual(form.$('.o_sms_count').text(), '15 characters, fits in 1 SMS (UNICODE) ',
            'Should be "15 characters, fits in 1 SMS (UNICODE) " for "Hêllo from Odoo"');
        // GSM-7 with 160c
        var text = Array(161).join('a');
        await testUtils.fields.editAndTrigger(form.$('.o_input'), text, 'input');
        assert.strictEqual(form.$('.o_sms_count').text(), '160 characters, fits in 1 SMS (GSM7) ',
            'Should be "160 characters, fits in 1 SMS (GSM7) " for 160 x "a"');
        // GSM-7 with 161c
        text = Array(162).join('a');
        await testUtils.fields.editAndTrigger(form.$('.o_input'), text, 'input');
        assert.strictEqual(form.$('.o_sms_count').text(), '161 characters, fits in 2 SMS (GSM7) ',
            'Should be "161 characters, fits in 2 SMS (GSM7) " for 161 x "a"');
        // Unicode with 70c
        text = Array(71).join('ê');
        await testUtils.fields.editAndTrigger(form.$('.o_input'), text, 'input');
        assert.strictEqual(form.$('.o_sms_count').text(), '70 characters, fits in 1 SMS (UNICODE) ',
            'Should be "70 characters, fits in 1 SMS (UNICODE) " for 70 x "ê"');
        // Unicode with 71c
        text = Array(72).join('ê');
        await testUtils.fields.editAndTrigger(form.$('.o_input'), text, 'input');
        assert.strictEqual(form.$('.o_sms_count').text(), '71 characters, fits in 2 SMS (UNICODE) ',
            'Should be "71 characters, fits in 2 SMS (UNICODE) " for 71 x "ê"');

        form.destroy();
    });
});
});
