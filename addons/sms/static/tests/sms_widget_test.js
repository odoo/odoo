/** @odoo-module **/

import { addFakeModel } from '@bus/../tests/helpers/model_definitions_helpers';
import { click, getFixture } from "@web/../tests/helpers/utils";
import FormView from 'web.FormView';
import ListView from 'web.ListView';
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { start, startServer } from '@mail/../tests/helpers/test_utils';
import testUtils from 'web.test_utils';

const createView = testUtils.createView;



QUnit.module('SmsWidget', (hooks) => {

    let target = undefined;
    let pyEnv = undefined;

    addFakeModel('fields.sms.emojis.partner', {
        message: {string: "message", type: "text"},
    });

    /**
     * Open the correct view based on inputs
     *
     * @param {string} model full name of the model to display
     * @param {string} viewArch layout of the view in xml
     * @param {number} recordId id of the record to open, new record created if falsy
     * @param {boolean} debug
     */
    async function openTestView(model, viewArch, recordId = null) {
        const views = {};
        const resModel = model;
        views[`${resModel},false,form`] = viewArch;
        const startParams = {serverData: {views}};
        const { openView } = await start(startParams);
        const openViewParams = {
            res_model: resModel,
            views: [[false, 'form']],
        };
        if (recordId) {
            openViewParams.res_id = recordId;
        }
        await openView(openViewParams);
    }

    hooks.beforeEach(async () => {
        pyEnv = await startServer();
        target = getFixture();
    });

    QUnit.test('Sms widgets are correctly rendered', async function (assert) {
        assert.expect(9);
        await openTestView('fields.sms.emojis.partner', `<form><sheet><field name="message" widget="sms_widget"/></sheet></form>`);

        assert.containsOnce(target, '.o_sms_count', "Should have a sms counter");
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "0 characters, fits in 0 SMS (GSM7) ");
        // GSM-7
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), "Hello from Odoo", 'input');
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "15 characters, fits in 1 SMS (GSM7) ");
        // GSM-7 with \n => this one count as 2 characters
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), "Hello from Odoo\n", 'input');
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "17 characters, fits in 1 SMS (GSM7) ");
        // Unicode => ê
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), "Hêllo from Odoo", 'input');
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "15 characters, fits in 1 SMS (UNICODE) ");
        // GSM-7 with 160c
        var text = Array(161).join('a');
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), text, 'input');
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "160 characters, fits in 1 SMS (GSM7) ");
        // GSM-7 with 161c
        text = Array(162).join('a');
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), text, 'input');
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "161 characters, fits in 2 SMS (GSM7) ");
        // Unicode with 70c
        text = Array(71).join('ê');
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), text, 'input');
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "70 characters, fits in 1 SMS (UNICODE) ");
        // Unicode with 71c
        text = Array(72).join('ê');
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), text, 'input');
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, "71 characters, fits in 2 SMS (UNICODE) ");
    });

    QUnit.test('SMS widgets update with emoji picker', async function (assert) {
        assert.expect(3);
        await openTestView('fields.sms.emojis.partner', `<form><sheet><field name="message" widget="sms_widget"/></sheet></form>`);

        assert.containsOnce(target, '.o_sms_count', "Should have a sms counter");

        // insert some text
        const baseString = "Hello from Odoo";
        await testUtils.fields.editAndTrigger(target.querySelector('.o_input'), baseString, 'input');

        // insert an emoji
        await click(target, ".o_field_sms_widget button");
        let emojiItem = target.querySelector(".o-mail-emoji-picker-content .o-emoji");
        let emojiItemCharacter = emojiItem.textContent;
        await click(emojiItem);

        // check everything is there
        let stringLength = baseString.length + emojiItemCharacter.length;
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, `${stringLength} characters, fits in 1 SMS (UNICODE) `,
                           "Should have included the length of the new emoji");

        // check insertion after selection (replacing selection)
        target.querySelector('.o_input').setSelectionRange(0, stringLength);
        await click(target, ".o_field_sms_widget button");
        emojiItem = target.querySelector(".o-mail-emoji-picker-content .o-emoji");
        emojiItemCharacter = emojiItem.textContent;
        await click(emojiItem);
        stringLength = emojiItemCharacter.length;
        assert.strictEqual(target.querySelector('.o_sms_count').textContent, `${stringLength} characters, fits in 1 SMS (UNICODE) `,
                           "Should have included the length of the new emoji and removed the length of the replaced characters");

    });

    QUnit.test('Sms widgets with non-empty initial value', async function (assert) {
        assert.expect(1);
        const recordId = pyEnv['fields.sms.emojis.partner'].create({ message: '123test' });
        await openTestView('fields.sms.emojis.partner', `<form><sheet><field name="message" widget="sms_widget" readonly="true"/></sheet></form>`, recordId);

        assert.strictEqual(target.querySelector('.o_field_text span').textContent, '123test', 'Should have the initial value');

    });

    QUnit.test('Sms widgets with empty initial value', async function (assert) {
        const recordId = pyEnv['fields.sms.emojis.partner'].create({ message: '' });
        assert.expect(1);
        await openTestView('fields.sms.emojis.partner', `<form><sheet><field name="message" widget="sms_widget" readonly="true"/></sheet></form>`, recordId);

        assert.strictEqual(target.querySelector('.o_field_text span').textContent, '',
            'Should have the empty initial value');

    });
});

QUnit.module('PhoneWidget', (hooks) => {

    let data = undefined;
    hooks.beforeEach(() => {
        data = {
            partner: {
                fields: {
                    message: {string: "message", type: "text"},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    mobile: {string: "mobile", type: "text"},
                },
                records: [{
                    id: 1,
                    message: "",
                    foo: 'yop',
                    mobile: "+32494444444",
                }, {
                    id: 2,
                    message: "",
                    foo: 'bayou',
                }],
            },
        };
        setupViewRegistries();
    });

    QUnit.test('phone field in editable list view on normal screens', async function (assert) {
        assert.expect(11);
        var doActionCount = 0;

        var list = await createView({
            View: ListView,
            model: 'partner',
            data: data,
            debug: true,
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

        assert.containsN(list, 'div.o_field_widget.o_form_uri.o_field_phone > a', 2,
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
        assert.containsN(list, 'div.o_field_widget.o_form_uri.o_field_phone > a', 2,
            "should still have links with correct classes");

        await testUtils.dom.click(list.$('tbody td:not(.o_list_record_selector) .o_field_phone_sms').first());
        assert.equal(doActionCount, 1, 'Only one action should have been executed');
        assert.containsNone(list, '.o_selected_row',
            'None of the list element should have been activated');

        list.destroy();
    });

    QUnit.test('readonly sms phone field is properly rerendered after been changed by onchange', async function (assert) {
        assert.expect(4);

        const NEW_PHONE = '+32595555555';

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: data,
            arch: '<form string="Partners">' +
                '<sheet>' +
                '<group>' +
                '<field name="foo" on_change="1"/>' + // onchange to update mobile in readonly mode directly
                '<field name="mobile" widget="phone" readonly="1"/>' + // readonly only, we don't want to go through write mode
                '</group>' +
                '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {mode: 'edit'},
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    return Promise.resolve({
                        value: {
                            mobile: NEW_PHONE, // onchange to update mobile in readonly mode directly
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        // check initial rendering
        assert.strictEqual(form.$('.o_field_phone').text(), "+32494444444",
            'Initial Phone text should be set');
        assert.strictEqual(form.$('.o_field_phone_sms').text(), 'SMS',
            'SMS button label should be rendered');

        // trigger the onchange to update phone field, but still in readonly mode
        await testUtils.fields.editInput($('input[name="foo"]'), 'someOtherFoo');

        // check rendering after changes
        assert.strictEqual(form.$('.o_field_phone').text(), NEW_PHONE,
            'Phone text should be updated');
        assert.strictEqual(form.$('.o_field_phone_sms').text(), 'SMS',
            'SMS button label should not be changed');

        form.destroy();
    });
});
