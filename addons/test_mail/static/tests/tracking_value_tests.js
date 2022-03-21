/** @odoo-module **/

import {
    beforeEach,
    start,
} from '@mail/../tests/helpers/test_utils';

import FormView from 'web.FormView';
import testUtils from 'web.test_utils';

QUnit.module('test_mail', {}, function () {
QUnit.module('tracking_value_tests.js', {
    async beforeEach() {
        await beforeEach(this);

        this.start = async params => {
            return start({
                arch: `<form>
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
                archs: { 'mail.message,false,list': '<tree/>' },
                data: this.data,
                hasView: true,
                model: 'mail.test.track.all',
                View: FormView,
                viewOptions: { mode: 'edit' },
                ...params,
            });
        };
    },
});

QUnit.test('basic rendering of tracking value (float type)', async function (assert) {
    assert.expect(8);

    this.data['mail.test.track.all'].records.push({ float_field: 12.30, id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('input[name=float_field]'), 45.67);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValue',
        "should display a tracking value"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueFieldName',
        "should display the name of the tracked field"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValueFieldName').textContent,
        "Float:",
        "should display the correct tracked field name (Float)",
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueOldValue',
        "should display the old value"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValueOldValue').textContent,
        "12.30",
        "should display the correct old value (12.30)",
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueSeparator',
        "should display the separator"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_trackingValueNewValue',
        "should display the new value"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValueNewValue').textContent,
        "45.67",
        "should display the correct new value (45.67)",
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type float: from non-0 to 0', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ float_field: 1, id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('input[name=float_field]'), 0);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Float:1.000.00",
        "should display the correct content of tracked field of type float: from non-0 to 0 (Float: 1.00 -> 0.00)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type float: from 0 to non-0', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ float_field: 0, id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('input[name=float_field]'), 1);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Float:0.001.00",
        "should display the correct content of tracked field of type float: from 0 to non-0 (Float: 0.00 -> 1.00)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type integer: from non-0 to 0', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1, integer_field: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('input[name=integer_field]'), 0);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Integer:10",
        "should display the correct content of tracked field of type integer: from non-0 to 0 (Integer: 1 -> 0)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type integer: from 0 to non-0', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1, integer_field: 0 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('input[name=integer_field]'), 1);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Integer:01",
        "should display the correct content of tracked field of type integer: from 0 to non-0 (Integer: 0 -> 1)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type monetary: from non-0 to 0', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1, monetary_field: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editSelect(form.$('div[name=monetary_field] > input'), 0);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Monetary:1.000.00",
        "should display the correct content of tracked field of type monetary: from non-0 to 0 (Monetary: 1.00 -> 0.00)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type monetary: from 0 to non-0', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1, monetary_field: 0 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editSelect(form.$('div[name=monetary_field] > input'), 1);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Monetary:0.001.00",
        "should display the correct content of tracked field of type monetary: from 0 to non-0 (Monetary: 0.00 -> 1.00)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type boolean: from true to false', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ boolean_field: true, id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    form.$('.custom-checkbox input').click();
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Boolean:YesNo",
        "should display the correct content of tracked field of type boolean: from true to false (Boolean: True -> False)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type boolean: from false to true', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    form.$('.custom-checkbox input').click();
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Boolean:NoYes",
        "should display the correct content of tracked field of type boolean: from false to true (Boolean: False -> True)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type char: from a string to empty string', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ char_field: 'Marc', id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('input[name=char_field]'), '');
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Char:MarcNone",
        "should display the correct content of tracked field of type char: from a string to empty string (Char: Marc -> None)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type char: from empty string to a string', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ char_field: '', id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('input[name=char_field]'), 'Marc');
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Char:NoneMarc",
        "should display the correct content of tracked field of type char: from empty string to a string (Char: None -> Marc)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type date: from no date to a set date', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ date_field: false, id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editAndTrigger(form.$('.o_datepicker[name=date_field] .o_datepicker_input'), '12/14/2018', ['change']);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Date:None12/14/2018",
        "should display the correct content of tracked field of type date: from no date to a set date (Date: None -> 12/14/2018)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type date: from a set date to no date', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ date_field: '2018-12-14', id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editAndTrigger(form.$('.o_datepicker[name=date_field] .o_datepicker_input'), '', ['change']);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Date:12/14/2018None",
        "should display the correct content of tracked field of type date: from a set date to no date (Date: 12/14/2018 -> None)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type datetime: from no date and time to a set date and time', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ datetime_field: false, id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editAndTrigger(form.$('.o_datepicker[name=datetime_field] .o_datepicker_input'), '12/14/2018 13:42:28', ['change']);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Datetime:None12/14/2018 13:42:28",
        "should display the correct content of tracked field of type datetime: from no date and time to a set date and time (Datetime: None -> 12/14/2018 13:42:28)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type datetime: from a set date and time to no date and time', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ datetime_field: '2018-12-14 13:42:28 ', id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editAndTrigger(form.$('.o_datepicker[name=datetime_field] .o_datepicker_input'), '', ['change']);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Datetime:12/14/2018 13:42:28None",
        "should display the correct content of tracked field of type datetime: from a set date and time to no date and time (Datetime: 12/14/2018 13:42:28 -> None)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type text: from some text to empty', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1, text_field: 'Marc' });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('textarea[name=text_field]'), '');
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Text:MarcNone",
        "should display the correct content of tracked field of type text: from some text to empty (Text: Marc -> None)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type text: from empty to some text', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1, text_field: '' });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editInput(form.$('textarea[name=text_field]'), 'Marc');
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Text:NoneMarc",
        "should display the correct content of tracked field of type text: from empty to some text (Text: None -> Marc)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type selection: from a selection to no selection', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1, selection_field: 'first' });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editSelect(form.$('select[name=selection_field]'), '');
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Selection:firstNone",
        "should display the correct content of tracked field of type selection: from a selection to no selection (Selection: first -> None)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type selection: from no selection to a selection', async function (assert) {
    assert.expect(1);

    this.data['mail.test.track.all'].records.push({ id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editSelect(form.$('select[name=selection_field]'), '"first"');
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Selection:Nonefirst",
        "should display the correct content of tracked field of type selection: from no selection to a selection (Selection: None -> first)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type many2one: from having a related record to no related record', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ display_name: 'Marc', id: 11 });
    this.data['mail.test.track.all'].records.push({ id: 1, many2one_field_id: 11 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.editAndTrigger(form.$('.o_field_many2one_selection input'), '', ['keyup']);
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Many2one:MarcNone",
        "should display the correct content of tracked field of type many2one: from having a related record to no related record (Many2one: Marc -> None)"
    );

    form.destroy();
});

QUnit.test('rendering of tracked field of type many2one: from no related record to having a related record', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ display_name: 'Marc', id: 11 });
    this.data['mail.test.track.all'].records.push({ id: 1 });
    const { afterNextRender, widget: form } = await this.start({ res_id: 1 });

    await testUtils.fields.many2one.clickOpenDropdown('many2one_field_id');
    await testUtils.fields.many2one.clickItem('many2one_field_id', 'Marc');
    await afterNextRender(() => testUtils.form.clickSave(form));
    assert.strictEqual(
        document.querySelector('.o_Message_trackingValue').textContent,
        "Many2one:NoneMarc",
        "should display the correct content of tracked field of type many2one: from no related record to having a related record (Many2one: None -> Marc)"
    );

    form.destroy();
});
});
