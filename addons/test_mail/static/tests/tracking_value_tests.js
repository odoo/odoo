/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { editInput, editSelect, selectDropdownItem, patchWithCleanup, patchTimeZone } from "@web/../tests/helpers/utils";

import session from 'web.session';
import testUtils from 'web.test_utils';

QUnit.module('test_mail', {}, function () {
QUnit.module('tracking_value_tests.js', {
    beforeEach() {
        const views = {
            'mail.test.track.all,false,form':
                `<form>
                    <sheet>
                        <field name="boolean_field"/>
                        <field name="char_field"/>
                        <field name="date_field"/>
                        <field name="datetime_field"/>
                        <field name="float_field"/>
                        <field name="integer_field"/>
                        <field name="monetary_field"/>
                        <field name="many2one_field_id"/>
                        <field name="selection_field"/>
                        <field name="text_field"/>
                    </sheet>
                    <div class="oe_chatter">
                        <field name="message_ids"/>
                    </div>
                </form>`,
        };
        this.start = async ({ res_id }) => {
            const { openFormView, ...remainder } = await start({
                serverData: { views },
            });
            await openFormView(
                {
                    res_model: 'mail.test.track.all',
                    res_id,
                },
                {
                    props: { mode: 'edit' },
                },
            );
            return remainder;
        };

        patchWithCleanup(session, {
            getTZOffset() {
                return 0;
            },
        });
    },
});

QUnit.test('basic rendering of tracking value (float type)', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ float_field: 12.30 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=float_field] input', 45.67);
    await click('.o_form_button_save');
    assert.containsOnce(
        document.body,
        '.o_TrackingValue',
        "should display a tracking value"
    );
    assert.containsOnce(
        document.body,
        '.o_TrackingValue_fieldName',
        "should display the name of the tracked field"
    );
    assert.strictEqual(
        document.querySelector('.o_TrackingValue_fieldName').textContent,
        "(Float)",
        "should display the correct tracked field name (Float)",
    );
    assert.containsOnce(
        document.body,
        '.o_TrackingValue_oldValue',
        "should display the old value"
    );
    assert.strictEqual(
        document.querySelector('.o_TrackingValue_oldValue').textContent,
        "12.30",
        "should display the correct old value (12.30)",
    );
    assert.containsOnce(
        document.body,
        '.o_TrackingValue_separator',
        "should display the separator"
    );
    assert.containsOnce(
        document.body,
        '.o_TrackingValue_newValue',
        "should display the new value"
    );
    assert.strictEqual(
        document.querySelector('.o_TrackingValue_newValue').textContent,
        "45.67",
        "should display the correct new value (45.67)",
    );
});

QUnit.test('rendering of tracked field of type float: from non-0 to 0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ float_field: 1 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=float_field] input', 0);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "1.000.00(Float)",
        "should display the correct content of tracked field of type float: from non-0 to 0 (1.00 -> 0.00 (Float))"
    );
});

QUnit.test('rendering of tracked field of type float: from 0 to non-0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ float_field: 0 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=float_field] input', 1);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "0.001.00(Float)",
        "should display the correct content of tracked field of type float: from 0 to non-0 (0.00 -> 1.00 (Float))"
    );
});

QUnit.test('rendering of tracked field of type integer: from non-0 to 0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ integer_field: 1 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=integer_field] input', 0);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "10(Integer)",
        "should display the correct content of tracked field of type integer: from non-0 to 0 (1 -> 0 (Integer))"
    );
});

QUnit.test('rendering of tracked field of type integer: from 0 to non-0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ integer_field: 0 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=integer_field] input', 1);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "01(Integer)",
        "should display the correct content of tracked field of type integer: from 0 to non-0 (0 -> 1 (Integer))"
    );
});

QUnit.test('rendering of tracked field of type monetary: from non-0 to 0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ monetary_field: 1 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=monetary_field] input', 0);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "1.000.00(Monetary)",
        "should display the correct content of tracked field of type monetary: from non-0 to 0 (1.00 -> 0.00 (Monetary))"
    );
});

QUnit.test('rendering of tracked field of type monetary: from 0 to non-0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ monetary_field: 0 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=monetary_field] input', 1);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "0.001.00(Monetary)",
        "should display the correct content of tracked field of type monetary: from 0 to non-0 (0.00 -> 1.00 (Monetary))"
    );
});

QUnit.test('rendering of tracked field of type boolean: from true to false', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ boolean_field: true });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    document.querySelector('.o_field_boolean input').click();
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "YesNo(Boolean)",
        "should display the correct content of tracked field of type boolean: from true to false (True -> False (Boolean))"
    );
});

QUnit.test('rendering of tracked field of type boolean: from false to true', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({});
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    document.querySelector('.o_field_boolean input').click();
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "NoYes(Boolean)",
        "should display the correct content of tracked field of type boolean: from false to true (False -> True (Boolean))"
    );
});

QUnit.test('rendering of tracked field of type char: from a string to empty string', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ char_field: 'Marc' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=char_field] input', '');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "MarcNone(Char)",
        "should display the correct content of tracked field of type char: from a string to empty string (Marc -> None (Char))"
    );
});

QUnit.test('rendering of tracked field of type char: from empty string to a string', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ char_field: '' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=char_field] input', 'Marc');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "NoneMarc(Char)",
        "should display the correct content of tracked field of type char: from empty string to a string (None -> Marc (Char))"
    );
});

QUnit.test('rendering of tracked field of type date: from no date to a set date', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ date_field: false });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('div[name=date_field] .o_datepicker .o_datepicker_input'), '12/14/2018', ['change']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "None12/14/2018(Date)",
        "should display the correct content of tracked field of type date: from no date to a set date (None -> 12/14/2018 (Date))"
    );
});

QUnit.test('rendering of tracked field of type date: from a set date to no date', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ date_field: '2018-12-14' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('div[name=date_field] .o_datepicker .o_datepicker_input'), '', ['change']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "12/14/2018None(Date)",
        "should display the correct content of tracked field of type date: from a set date to no date (12/14/2018 -> None (Date))"
    );
});

QUnit.test('rendering of tracked field of type datetime: from no date and time to a set date and time', async function (assert) {
    assert.expect(2);

    patchTimeZone(180);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ datetime_field: false });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('div[name=datetime_field] .o_datepicker .o_datepicker_input'), '12/14/2018 13:42:28', ['change']);
    await click('.o_form_button_save');
    const savedRecord = pyEnv.getData()["mail.test.track.all"].records.find(({id}) => id === mailTestTrackAllId1);
    assert.strictEqual(savedRecord.datetime_field, '2018-12-14 10:42:28');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "None12/14/2018 13:42:28(Datetime)",
        "should display the correct content of tracked field of type datetime: from no date and time to a set date and time (None -> 12/14/2018 13:42:28 (Datetime))"
    );
});

QUnit.test('rendering of tracked field of type datetime: from a set date and time to no date and time', async function (assert) {
    assert.expect(1);

    patchTimeZone(180)

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ datetime_field: '2018-12-14 13:42:28 ' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('div[name=datetime_field] .o_datepicker .o_datepicker_input'), '', ['change']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "12/14/2018 16:42:28None(Datetime)",
        "should display the correct content of tracked field of type datetime: from a set date and time to no date and time (12/14/2018 13:42:28 -> None (Datetime))"
    );
});

QUnit.test('rendering of tracked field of type text: from some text to empty', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ text_field: 'Marc' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=text_field] textarea', '');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "MarcNone(Text)",
        "should display the correct content of tracked field of type text: from some text to empty (Marc -> None (Text))"
    );
});

QUnit.test('rendering of tracked field of type text: from empty to some text', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ text_field: '' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, 'div[name=text_field] textarea', 'Marc');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "NoneMarc(Text)",
        "should display the correct content of tracked field of type text: from empty to some text (None -> Marc (Text))"
    );
});

QUnit.test('rendering of tracked field of type selection: from a selection to no selection', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ selection_field: 'first' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editSelect(document.body, 'div[name=selection_field] select', false);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "firstNone(Selection)",
        "should display the correct content of tracked field of type selection: from a selection to no selection (first -> None (Selection))"
    );
});

QUnit.test('rendering of tracked field of type selection: from no selection to a selection', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({});
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editSelect(document.body, 'div[name=selection_field] select', '"first"');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Nonefirst(Selection)",
        "should display the correct content of tracked field of type selection: from no selection to a selection (None -> first (Selection))"
    );
});

QUnit.test('rendering of tracked field of type many2one: from having a related record to no related record', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: 'Marc' });
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ many2one_field_id: resPartnerId1 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await editInput(document.body, ".o_field_many2one_selection input", '')
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "MarcNone(Many2one)",
        "should display the correct content of tracked field of type many2one: from having a related record to no related record (Marc -> None (Many2one))"
    );
});

QUnit.test('rendering of tracked field of type many2one: from no related record to having a related record', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['res.partner'].create({ display_name: 'Marc' });
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({});
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await selectDropdownItem(document.body, "many2one_field_id", "Marc")
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "NoneMarc(Many2one)",
        "should display the correct content of tracked field of type many2one: from no related record to having a related record (None -> Marc (Many2one))"
    );
});
});
