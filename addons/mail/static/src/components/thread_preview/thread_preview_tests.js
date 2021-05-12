/** @odoo-module **/

import ThreadPreview from '@mail/components/thread_preview/thread_preview';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} from '@mail/utils/test_utils';

const components = { ThreadPreview };

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_preview', {}, function () {
QUnit.module('thread_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadPreviewComponent = async props => {
            await createRootComponent(this, components.ThreadPreview, {
                props,
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('mark as read', async function (assert) {
    assert.expect(8);
    this.data['mail.channel'].records.push({
        id: 11,
        message_unread_counter: 1,
    });
    this.data['mail.message'].records.push({
        id: 100,
        model: 'mail.channel',
        res_id: 11,
    });

    await this.start({
        hasChatWindow: true,
        async mockRPC(route, args) {
            if (route.includes('channel_seen')) {
                assert.step('channel_seen');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    await this.createThreadPreviewComponent({ threadLocalId: thread.localId });
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_markAsRead',
        "should have the mark as read button"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_counter',
        "should have an unread counter"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadPreview_markAsRead').click()
    );
    assert.verifySteps(
        ['channel_seen'],
        "should have marked the thread as seen"
    );
    assert.hasClass(
        document.querySelector('.o_ThreadPreview'),
        'o-muted',
        "should be muted once marked as read"
    );
    assert.containsNone(
        document.body,
        '.o_ThreadPreview_markAsRead',
        "should no longer have the mark as read button"
    );
    assert.containsNone(
        document.body,
        '.o_ThreadPreview_counter',
        "should no longer have an unread counter"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have opened the thread"
    );
});

QUnit.test('tracking value of float type changed displayed in the system window', async function (assert) {
    assert.expect(8);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "float",
        new_value: 45.67,
        old_value: 12.3,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValue',
        "should display a tracking value"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueFieldName',
        "should display the name of the tracked field"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValueFieldName').textContent,
        "Total:",
        "should display the correct tracked field name (Total)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueOldValue',
        "should display the old value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValueOldValue').textContent,
        "12.30",
        "should display the correct old value (12.30)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueSeparator',
        "should display the separator"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueNewValue',
        "should display the new value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValueNewValue').textContent,
        "45.67",
        "should display the correct new value (45.67)",
    );
});

QUnit.test('tracking value of type integer: from non-0 to 0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "integer",
        new_value: 0,
        old_value: 1,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Total:10",
        "should display the correct content of tracked field of type integer: from non-0 to 0 (Total: 1 -> 0)"
    );
});

QUnit.test('tracking value of type integer: from 0 to non-0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "integer",
        new_value: 1,
        old_value: 0,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Total:01",
        "should display the correct content of tracked field of type integer: from 0 to non-0 (Total: 0 -> 1)"
    );
});

QUnit.test('tracking value of type float: from non-0 to 0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "float",
        new_value: 0,
        old_value: 1,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Total:1.000.00",
        "should display the correct content of tracked field of type float: from non-0 to 0 (Total: 1.00 -> 0.00)"
    );});

QUnit.test('tracking value of type float: from 0 to non-0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "float",
        new_value: 1,
        old_value: 0,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Total:0.001.00",
        "should display the correct content of tracked field of type float: from 0 to non-0 (Total: 0.00 -> 1.00)"
    );
});

QUnit.test('tracking value of type monetary: from non-0 to 0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "monetary",
        new_value: 0,
        old_value: 1,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Total:1.000.00",
        "should display the correct content of tracked field of type monetary: from non-0 to 0 (Total: 1.00 -> 0.00)"
    );
});

QUnit.test('tracking value of type monetary: from 0 to non-0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "monetary",
        new_value: 1,
        old_value: 0,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Total:0.001.00",
        "should display the correct content of tracked field of type monetary: from non-0 to 0 (Total: 1.00 -> 0.00)"
    );
});

QUnit.test('tracking value of type boolean: from true to false changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Is Ready",
        field_type: "boolean",
        new_value: false,
        old_value: true,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Is Ready:TrueFalse",
        "should display the correct content of tracked field of type boolean: from true to false (Is Ready: True -> False)"
    );
});

QUnit.test('tracking value of type boolean: from false to true changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Is Ready",
        field_type: "boolean",
        new_value: true,
        old_value: false,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Is Ready:FalseTrue",
        "should display the correct content of tracked field of type boolean: from false to true (Is Ready: False -> True)"
    );
});

QUnit.test('tracking value of type char: from a string to empty string changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Name",
        field_type: "char",
        new_value: "",
        old_value: "Marc",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type char: from a string to empty string (Name: Marc ->)"
    );
});

QUnit.test('tracking value of type char: from empty string to a string changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Name",
        field_type: "char",
        new_value: "Marc",
        old_value: "",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type char: from empty string to a string (Name: -> Marc)"
    );
});

QUnit.test('tracking value of type date: from no date to a set date changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Deadline",
        field_type: "date",
        new_value: "2018-12-14",
        old_value: false,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Deadline:12/14/2018",
        "should display the correct content of tracked field of type date: from no date to a set date (Deadline: -> 12/14/2018)"
    );
});

QUnit.test('tracking value of type date: from a set date to no date changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Deadline",
        field_type: "date",
        new_value: false,
        old_value: "2018-12-14",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Deadline:12/14/2018",
        "should display the correct content of tracked field of type date: from a set date to no date (Deadline: 12/14/2018 ->)"
    );
});

QUnit.test('tracking value of type datetime: from no date and time to a set date and time changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Deadline",
        field_type: "datetime",
        new_value: "2018-12-14 13:42:28",
        old_value: false,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Deadline:12/14/2018 13:42:28",
        "should display the correct content of tracked field of type datetime: from no date and time to a set date and time (Deadline: -> 12/14/2018 13:42:28)"
    );
});

QUnit.test('tracking value of type datetime: from a set date and time to no date and time changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Deadline",
        field_type: "datetime",
        new_value: false,
        old_value: "2018-12-14 13:42:28",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Deadline:12/14/2018 13:42:28",
        "should display the correct content of tracked field of type datetime: from a set date and time to no date and time (Deadline: 12/14/2018 13:42:28 ->)"
    );
});

QUnit.test('tracking value of type text: from some text to empty changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Name",
        field_type: "text",
        new_value: "",
        old_value: "Marc",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type text: from some text to empty (Name: Marc ->)"
    );
});

QUnit.test('tracking value of type text: from empty to some text changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Name",
        field_type: "text",
        new_value: "Marc",
        old_value: "",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type text: from empty to some text (Name: -> Marc)"
    );
});

QUnit.test('tracking value of type selection: from a selection to no selection changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "State",
        field_type: "selection",
        new_value: "",
        old_value: "ok",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "State:ok",
        "should display the correct content of tracked field of type selection: from a selection to no selection (State: ok ->)"
    );
});

QUnit.test('tracking value of type selection: from no selection to a selection changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "State",
        field_type: "selection",
        new_value: "ok",
        old_value: "",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "State:ok",
        "should display the correct content of tracked field of type selection: from no selection to a selection (State: -> ok)"
    );
});

QUnit.test('tracking value of type many2one: from having a related record to no related record changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Author",
        field_type: "many2one",
        new_value: "",
        old_value: "Marc",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Author:Marc",
        "should display the correct content of tracked field of type many2one: from having a related record to no related record (Author: Marc ->)"
    );
});

QUnit.test('tracking value of type many2one: from no related record to having a related record changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Author",
        field_type: "many2one",
        new_value: "Marc",
        old_value: "",
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValue').textContent,
        "Author:Marc",
        "should display the correct content of tracked field of type many2one: from no related record to having a related record (Author: -> Marc)"
    );
});

QUnit.test('tracking value of type monetary changed displayed in the system window', async function (assert) {
    assert.expect(8);
    this.data['mail.channel'].records.push({
        id: 11,
        name: 'Test Channel',
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Revenue",
        field_type: "monetary",
        currency_id: 1,
        new_value: 500,
        old_value: 1000,
        mail_message_id: 21,
    });
    await this.start({
        hasMessagingMenu: true,
        env: {
            session: {
                currencies: { 1: { symbol: '$', position: 'before' } },
            },
        },    
    });
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValue',
        "should display a tracking value"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueFieldName',
        "should display the name of the tracked field"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValueFieldName').textContent,
        "Revenue:",
        "should display the correct tracked field name (Revenue)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueOldValue',
        "should display the old value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValueOldValue').innerHTML,
        "$ 1000.00",
        "should display the correct old value with the currency symbol ($ 1000.00)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueSeparator',
        "should display the separator"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_trackingValueNewValue',
        "should display the new value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_trackingValueNewValue').innerHTML,
        "$ 500.00",
        "should display the correct new value with the currency symbol ($ 500.00)",
    );
});

});
});
});
