/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from "@web/../tests/helpers/utils";

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
            const { openView, ...remainder } = await start({
                serverData: { views },
            });
            await openView(
                {
                    res_model: 'mail.test.track.all',
                    res_id,
                    views: [[false, 'form']],
                },
                { mode: 'edit' }
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

    await testUtils.fields.editInput(document.querySelector('input[name=float_field]'), 45.67);
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
        "Float:",
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

    await testUtils.fields.editInput(document.querySelector('input[name=float_field]'), 0);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Float:1.000.00",
        "should display the correct content of tracked field of type float: from non-0 to 0 (Float: 1.00 -> 0.00)"
    );
});

QUnit.test('rendering of tracked field of type float: from 0 to non-0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ float_field: 0 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editInput(document.querySelector('input[name=float_field]'), 1);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Float:0.001.00",
        "should display the correct content of tracked field of type float: from 0 to non-0 (Float: 0.00 -> 1.00)"
    );
});

QUnit.test('rendering of tracked field of type integer: from non-0 to 0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ integer_field: 1 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editInput(document.querySelector('input[name=integer_field]'), 0);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Integer:10",
        "should display the correct content of tracked field of type integer: from non-0 to 0 (Integer: 1 -> 0)"
    );
});

QUnit.test('rendering of tracked field of type integer: from 0 to non-0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ integer_field: 0 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editInput(document.querySelector('input[name=integer_field]'), 1);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Integer:01",
        "should display the correct content of tracked field of type integer: from 0 to non-0 (Integer: 0 -> 1)"
    );
});

QUnit.test('rendering of tracked field of type monetary: from non-0 to 0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ monetary_field: 1 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editSelect(document.querySelector('div[name=monetary_field] > input'), 0);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Monetary:1.000.00",
        "should display the correct content of tracked field of type monetary: from non-0 to 0 (Monetary: 1.00 -> 0.00)"
    );
});

QUnit.test('rendering of tracked field of type monetary: from 0 to non-0', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ monetary_field: 0 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editSelect(document.querySelector('div[name=monetary_field] > input'), 1);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Monetary:0.001.00",
        "should display the correct content of tracked field of type monetary: from 0 to non-0 (Monetary: 0.00 -> 1.00)"
    );
});

QUnit.test('rendering of tracked field of type boolean: from true to false', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ boolean_field: true });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    document.querySelector('.custom-checkbox input').click();
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Boolean:YesNo",
        "should display the correct content of tracked field of type boolean: from true to false (Boolean: True -> False)"
    );
});

QUnit.test('rendering of tracked field of type boolean: from false to true', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({});
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    document.querySelector('.custom-checkbox input').click();
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Boolean:NoYes",
        "should display the correct content of tracked field of type boolean: from false to true (Boolean: False -> True)"
    );
});

QUnit.test('rendering of tracked field of type char: from a string to empty string', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ char_field: 'Marc' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editInput(document.querySelector('input[name=char_field]'), '');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Char:MarcNone",
        "should display the correct content of tracked field of type char: from a string to empty string (Char: Marc -> None)"
    );
});

QUnit.test('rendering of tracked field of type char: from empty string to a string', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ char_field: '' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editInput(document.querySelector('input[name=char_field]'), 'Marc');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Char:NoneMarc",
        "should display the correct content of tracked field of type char: from empty string to a string (Char: None -> Marc)"
    );
});

QUnit.test('rendering of tracked field of type date: from no date to a set date', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ date_field: false });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('.o_datepicker[name=date_field] .o_datepicker_input'), '12/14/2018', ['change']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Date:None12/14/2018",
        "should display the correct content of tracked field of type date: from no date to a set date (Date: None -> 12/14/2018)"
    );
});

QUnit.test('rendering of tracked field of type date: from a set date to no date', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ date_field: '2018-12-14' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('.o_datepicker[name=date_field] .o_datepicker_input'), '', ['change']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Date:12/14/2018None",
        "should display the correct content of tracked field of type date: from a set date to no date (Date: 12/14/2018 -> None)"
    );
});

QUnit.test('rendering of tracked field of type datetime: from no date and time to a set date and time', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ datetime_field: false });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('.o_datepicker[name=datetime_field] .o_datepicker_input'), '12/14/2018 13:42:28', ['change']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Datetime:None12/14/2018 13:42:28",
        "should display the correct content of tracked field of type datetime: from no date and time to a set date and time (Datetime: None -> 12/14/2018 13:42:28)"
    );
});

QUnit.test('rendering of tracked field of type datetime: from a set date and time to no date and time', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ datetime_field: '2018-12-14 13:42:28 ' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('.o_datepicker[name=datetime_field] .o_datepicker_input'), '', ['change']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Datetime:12/14/2018 13:42:28None",
        "should display the correct content of tracked field of type datetime: from a set date and time to no date and time (Datetime: 12/14/2018 13:42:28 -> None)"
    );
});

QUnit.test('rendering of tracked field of type text: from some text to empty', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ text_field: 'Marc' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editInput(document.querySelector('textarea[name=text_field]'), '');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Text:MarcNone",
        "should display the correct content of tracked field of type text: from some text to empty (Text: Marc -> None)"
    );
});

QUnit.test('rendering of tracked field of type text: from empty to some text', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ text_field: '' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editInput(document.querySelector('textarea[name=text_field]'), 'Marc');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Text:NoneMarc",
        "should display the correct content of tracked field of type text: from empty to some text (Text: None -> Marc)"
    );
});

QUnit.test('rendering of tracked field of type selection: from a selection to no selection', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ selection_field: 'first' });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editSelect(document.querySelector('select[name=selection_field]'), '');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Selection:firstNone",
        "should display the correct content of tracked field of type selection: from a selection to no selection (Selection: first -> None)"
    );
});

QUnit.test('rendering of tracked field of type selection: from no selection to a selection', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({});
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editSelect(document.querySelector('select[name=selection_field]'), '"first"');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Selection:Nonefirst",
        "should display the correct content of tracked field of type selection: from no selection to a selection (Selection: None -> first)"
    );
});

QUnit.test('rendering of tracked field of type many2one: from having a related record to no related record', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: 'Marc' });
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({ many2one_field_id: resPartnerId1 });
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.editAndTrigger(document.querySelector('.o_field_many2one_selection input'), '', ['keyup']);
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Many2one:MarcNone",
        "should display the correct content of tracked field of type many2one: from having a related record to no related record (Many2one: Marc -> None)"
    );
});

QUnit.test('rendering of tracked field of type many2one: from no related record to having a related record', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['res.partner'].create({ display_name: 'Marc' });
    const mailTestTrackAllId1 = pyEnv['mail.test.track.all'].create({});
    const { click } = await this.start({ res_id: mailTestTrackAllId1 });

    await testUtils.fields.many2one.clickOpenDropdown('many2one_field_id');
    await testUtils.fields.many2one.clickItem('many2one_field_id', 'Marc');
    await click('.o_form_button_save');
    assert.strictEqual(
        document.querySelector('.o_TrackingValue').textContent,
        "Many2one:NoneMarc",
        "should display the correct content of tracked field of type many2one: from no related record to having a related record (Many2one: None -> Marc)"
    );
});
});
