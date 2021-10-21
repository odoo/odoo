/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

import Bus from 'web.Bus';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_needaction_preview', {}, function () {
QUnit.module('thread_needaction_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadNeedactionPreviewComponent = async props => {
            await createRootMessagingComponent(this, "ThreadNeedactionPreview", {
                props,
                target: this.widget.el
            });
        };

        this.start = async params => {
            const res = await start(Object.assign({}, params, {
                data: this.data,
            }));
            const { afterEvent, env, widget } = res;
            this.afterEvent = afterEvent;
            this.env = env;
            this.widget = widget;
            return res;
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
    const { createMessagingMenuComponent } = await this.start({
        hasChatWindow: true,
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
    await createMessagingMenuComponent();
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
    const { createMessagingMenuComponent } = await this.start({
        hasChatWindow: true,
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
    await createMessagingMenuComponent();
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
    const { createMessagingMenuComponent } = await this.start({
        env: { bus },
        hasChatWindow: true,
    });
    await createMessagingMenuComponent();
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
    const { createMessagingMenuComponent } = await this.start({
        hasChatWindow: true,
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
    await createMessagingMenuComponent();
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
    const { createMessagingMenuComponent } = await this.start({ hasChatWindow: true });
    await createMessagingMenuComponent();
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
    const { createMessagingMenuComponent } = await this.start({ hasChatWindow: true });
    await createMessagingMenuComponent();
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

});
});
});
