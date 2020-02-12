odoo.define('sms.sms_widget_tests', function (require) {
"use strict";

var config = require('web.config');
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    message: {string: "message", type: "text"},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                },
                records: [{
                    id: 1,
                    message: "",
                    foo: 'yop',
                }, {
                    id: 2,
                    message: "",
                    foo: 'bayou',
                }]
            },
            visitor: {
                fields: {
                    mobile: {string: "mobile", type: "text"},
                },
                records: [{
                    id: 1,
                    mobile: "+32494444444",
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

    QUnit.test('Sms widgets with non-empty initial value', async function (assert) {
        assert.expect(1);
        var form = await createView({
            View: FormView,
            model: 'visitor',
            data: this.data,
            arch: `<form><sheet><field name="mobile" widget="sms_widget"/></sheet></form>`,
            res_id: 1,
            res_ids: [1],
        });

        assert.strictEqual(form.$('.o_field_text').text(), '+32494444444',
            'Should have the initial value');

        form.destroy();
    });

    QUnit.test('Sms widgets with empty initial value', async function (assert) {
        assert.expect(1);
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form><sheet><field name="message" widget="sms_widget"/></sheet></form>`,
            res_id: 1,
            res_ids: [1],
        });

        assert.strictEqual(form.$('.o_field_text').text(), '',
            'Should have the empty initial value');

        form.destroy();
    });

    QUnit.module('PhoneWidget');

    QUnit.test('phone field in editable list view on normal screens', async function (assert) {
        assert.expect(11);
        var doActionCount = 0;

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            debug:true,
            arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
            intercepts: {
                do_action(ev) {
                    assert.equal(ev.data.action.res_model, 'sms.composer',
                        'The action to send an SMS should have been executed');
                    doActionCount += 1;
                }
            }
        });

        assert.containsN(list, 'tbody td:not(.o_list_record_selector)', 4);
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'yopSMS',
            "value should be displayed properly with a link to send SMS");

        assert.containsN(list, 'a.o_field_widget.o_form_uri', 2,
            "should have the correct classnames");

        // Edit a line and check the result
        var $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(),'o_selected_row', 'should be set as edit mode');
        assert.strictEqual($cell.find('input').val(), 'yop',
            'should have the corect value in internal input');
        await testUtils.fields.editInput($cell.find('input'), 'new');

        // save
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        $cell = list.$('tbody td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($cell.parent(), 'o_selected_row', 'should not be in edit mode anymore');
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').first().text(), 'newSMS',
            "value should be properly updated");
        assert.containsN(list, 'a.o_field_widget.o_form_uri', 2,
            "should still have links with correct classes");

        await testUtils.dom.click(list.$('tbody td:not(.o_list_record_selector) .o_field_phone_sms').first());
        assert.equal(doActionCount, 1, 'Only one action should have been executed');
        assert.containsNone(list, '.o_selected_row',
            'None of the list element should have been activated');

        list.destroy();
    });
});
});
