/** @odoo-module **/

import ThreadNeedactionPreview from '@mail/components/thread_needaction_preview/thread_needaction_preview';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} from '@mail/utils/test_utils';

import Bus from 'web.Bus';

const components = { ThreadNeedactionPreview };

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_needaction_preview', {}, function () {
QUnit.module('thread_needaction_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadNeedactionPreviewComponent = async props => {
            await createRootComponent(this, components.ThreadNeedactionPreview, {
                props,
                target: this.widget.el
            });
        };

        this.start = async params => {
            const { afterEvent, env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.afterEvent = afterEvent;
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('mark as read', async function (assert) {
    assert.expect(5);

    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    await this.start({
        hasChatWindow: true,
        hasMessagingMenu: true,
        async mockRPC(route, args) {
            if (route.includes('mark_all_as_read')) {
                assert.step('mark_all_as_read');
                assert.deepEqual(
                    args.kwargs.domain,
                    [
                        ['model', '=', 'res.partner'],
                        ['res_id', '=', 11],
                    ],
                    "should mark all as read the correct thread"
                );
            }
            return this._super(...arguments);
        },
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_markAsRead',
        "should have 1 mark as read button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview_markAsRead').click()
    );
    assert.verifySteps(
        ['mark_all_as_read'],
        "should have marked the thread as read"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have opened the thread"
    );
});

QUnit.test('click on preview should mark as read and open the thread', async function (assert) {
    assert.expect(6);

    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    await this.start({
        hasChatWindow: true,
        hasMessagingMenu: true,
        async mockRPC(route, args) {
            if (route.includes('mark_all_as_read')) {
                assert.step('mark_all_as_read');
                assert.deepEqual(
                    args.kwargs.domain,
                    [
                        ['model', '=', 'res.partner'],
                        ['res_id', '=', 11],
                    ],
                    "should mark all as read the correct thread"
                );
            }
            return this._super(...arguments);
        },
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no chat window initially"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview').click()
    );
    assert.verifySteps(
        ['mark_all_as_read'],
        "should have marked the message as read on clicking on the preview"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread on clicking on the preview"
    );
});

QUnit.test('click on expand from chat window should close the chat window and open the form view', async function (assert) {
    assert.expect(8);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.res_id,
            11,
            "should redirect to the id of the thread"
        );
        assert.strictEqual(
            payload.action.res_model,
            'res.partner',
            "should redirect to the model of the thread"
        );
    });
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    await this.start({
        env: { bus },
        hasChatWindow: true,
        hasMessagingMenu: true,
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread on clicking on the preview"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindowHeader_commandExpand',
        "should have an expand button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandExpand').click()
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have closed the chat window on clicking expand"
    );
    assert.verifySteps(
        ['do_action'],
        "should have done an action to open the form view"
    );
});

QUnit.test('[technical] opening a non-channel chat window should not call channel_fold', async function (assert) {
    // channel_fold should not be called when opening non-channels in chat
    // window, because there is no server sync of fold state for them.
    assert.expect(3);

    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    await this.start({
        hasChatWindow: true,
        hasMessagingMenu: true,
        async mockRPC(route, args) {
            if (route.includes('channel_fold')) {
                const message = "should not call channel_fold when opening a non-channel chat window";
                assert.step(message);
                console.error(message);
                throw Error(message);
            }
            return this._super(...arguments);
        },
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no chat window initially"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the chat window on clicking on the preview"
    );
});

QUnit.test('preview should display last needaction message preview even if there is a more recent message that is not needaction in the thread', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({
        id: 11,
        name: "Stranger",
    });
    this.data['mail.message'].records.push({
        author_id: 11,
        body: "I am the oldest but needaction",
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.message'].records.push({
        author_id: this.data.currentPartnerId,
        body: "I am more recent",
        id: 22,
        model: 'res.partner',
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    await this.start({
        hasChatWindow: true,
        hasMessagingMenu: true,
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_inlineText',
        "should have a preview from the last message"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_inlineText').textContent,
        'Stranger: I am the oldest but needaction',
        "the displayed message should be the one that needs action even if there is a more recent message that is not needaction on the thread"
    );
});

QUnit.test('chat window header should not have unread counter for non-channel thread', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 11 });
    this.data['mail.message'].records.push({
        author_id: 11,
        body: 'not empty',
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    await this.start({
        hasChatWindow: true,
        hasMessagingMenu: true,
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    await afterNextRender(() =>
        document.querySelector('.o_ThreadNeedactionPreview').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the chat window on clicking on the preview"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindowHeader_counter',
        "chat window header should not have unread counter for non-channel thread"
    );
});

QUnit.test('tracking value of float type changed displayed in the system window', async function (assert) {
    assert.expect(8);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValue',
        "should display a tracking value"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueFieldName',
        "should display the name of the tracked field"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValueFieldName').textContent,
        "Total:",
        "should display the correct tracked field name (Total)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueOldValue',
        "should display the old value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValueOldValue').textContent,
        "12.30",
        "should display the correct old value (12.30)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueSeparator',
        "should display the separator"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueNewValue',
        "should display the new value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValueNewValue').textContent,
        "45.67",
        "should display the correct new value (45.67)",
    );
});

QUnit.test('tracking value of type integer: from non-0 to 0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
    });
    this.data['mail.tracking.value'].records.push({
        changed_field: "Total",
        field_type: "integer",
        new_value: 0,
        old_value: 1,
        mail_message_id: 21,
    });
    await this.start({
        debug: true,
        hasMessagingMenu: true,
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    //await new Promise((resolve, reject) =>{});
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Total:10",
        "should display the correct content of tracked field of type integer: from non-0 to 0 (Total: 1 -> 0)"
    );
});

QUnit.test('tracking value of type integer: from 0 to non-0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Total:01",
        "should display the correct content of tracked field of type integer: from 0 to non-0 (Total: 0 -> 1)"
    );
});

QUnit.test('tracking value of type float: from non-0 to 0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Total:1.000.00",
        "should display the correct content of tracked field of type float: from non-0 to 0 (Total: 1.00 -> 0.00)"
    );});

QUnit.test('tracking value of type float: from 0 to non-0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Total:0.001.00",
        "should display the correct content of tracked field of type float: from 0 to non-0 (Total: 0.00 -> 1.00)"
    );
});

QUnit.test('tracking value of type monetary: from non-0 to 0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Total:1.000.00",
        "should display the correct content of tracked field of type monetary: from non-0 to 0 (Total: 1.00 -> 0.00)"
    );
});

QUnit.test('tracking value of type monetary: from 0 to non-0 changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Total:0.001.00",
        "should display the correct content of tracked field of type monetary: from non-0 to 0 (Total: 1.00 -> 0.00)"
    );
});

QUnit.test('tracking value of type boolean: from true to false changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Is Ready:TrueFalse",
        "should display the correct content of tracked field of type boolean: from true to false (Is Ready: True -> False)"
    );
});

QUnit.test('tracking value of type boolean: from false to true changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Is Ready:FalseTrue",
        "should display the correct content of tracked field of type boolean: from false to true (Is Ready: False -> True)"
    );
});

QUnit.test('tracking value of type char: from a string to empty string changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type char: from a string to empty string (Name: Marc ->)"
    );
});

QUnit.test('tracking value of type char: from empty string to a string changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type char: from empty string to a string (Name: -> Marc)"
    );
});

QUnit.test('tracking value of type date: from no date to a set date changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Deadline:12/14/2018",
        "should display the correct content of tracked field of type date: from no date to a set date (Deadline: -> 12/14/2018)"
    );
});

QUnit.test('tracking value of type date: from a set date to no date changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Deadline:12/14/2018",
        "should display the correct content of tracked field of type date: from a set date to no date (Deadline: 12/14/2018 ->)"
    );
});

QUnit.test('tracking value of type datetime: from no date and time to a set date and time changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Deadline:12/14/2018 13:42:28",
        "should display the correct content of tracked field of type datetime: from no date and time to a set date and time (Deadline: -> 12/14/2018 13:42:28)"
    );
});

QUnit.test('tracking value of type datetime: from a set date and time to no date and time changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Deadline:12/14/2018 13:42:28",
        "should display the correct content of tracked field of type datetime: from a set date and time to no date and time (Deadline: 12/14/2018 13:42:28 ->)"
    );
});

QUnit.test('tracking value of type text: from some text to empty changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type text: from some text to empty (Name: Marc ->)"
    );
});

QUnit.test('tracking value of type text: from empty to some text changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Name:Marc",
        "should display the correct content of tracked field of type text: from empty to some text (Name: -> Marc)"
    );
});

QUnit.test('tracking value of type selection: from a selection to no selection changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "State:ok",
        "should display the correct content of tracked field of type selection: from a selection to no selection (State: ok ->)"
    );
});

QUnit.test('tracking value of type selection: from no selection to a selection changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "State:ok",
        "should display the correct content of tracked field of type selection: from no selection to a selection (State: -> ok)"
    );
});

QUnit.test('tracking value of type many2one: from having a related record to no related record changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Author:Marc",
        "should display the correct content of tracked field of type many2one: from having a related record to no related record (Author: Marc ->)"
    );
});

QUnit.test('tracking value of type many2one: from no related record to having a related record changed displayed in the system window', async function (assert) {
    assert.expect(1);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValue').textContent,
        "Author:Marc",
        "should display the correct content of tracked field of type many2one: from no related record to having a related record (Author: -> Marc)"
    );
});

QUnit.test('tracking value of type monetary changed displayed in the system window', async function (assert) {
    assert.expect(8);
    this.data['mail.message'].records.push({
        id: 21,
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 21,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: this.data.currentPartnerId,
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
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread.model === 'mail.box' && threadCache.thread.id === 'inbox';
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValue',
        "should display a tracking value"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueFieldName',
        "should display the name of the tracked field"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValueFieldName').textContent,
        "Revenue:",
        "should display the correct tracked field name (Revenue)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueOldValue',
        "should display the old value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValueOldValue').innerHTML,
        "$ 1000.00",
        "should display the correct old value with the currency symbol ($ 1000.00)",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueSeparator',
        "should display the separator"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_trackingValueNewValue',
        "should display the new value"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_trackingValueNewValue').innerHTML,
        "$ 500.00",
        "should display the correct new value with the currency symbol ($ 500.00)",
    );
});

});
});
});
