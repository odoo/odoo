odoo.define('mail/static/src/components/discuss/tests/discuss_moderation_tests.js', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_moderation_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        if (this.widget) {
            this.widget.destroy();
        }
        utilsAfterEach(this);
    },
});

QUnit.test('moderated channel with pending moderation message', async function (assert) {
    assert.expect(37);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [20],
    });
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        channel_ids: [20],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await this.start();

    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.moderation.localId
            }"]
        `),
        "should display the moderation box in the sidebar"
    );
    const mailboxCounter = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.messaging.moderation.localId
        }"]
        .o_DiscussSidebarItem_counter
    `);
    assert.ok(
        mailboxCounter,
        "there should be a counter next to the moderation mailbox in the sidebar"
    );
    assert.strictEqual(
        mailboxCounter.textContent.trim(),
        "1",
        "the mailbox counter of the moderation mailbox should display '1'"
    );

    // 1. go to moderation mailbox
    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.moderation.localId
            }"]
        `).click()
    );
    // check message
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should be only one message in moderation box"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_content').textContent,
        "test",
        "this message pending moderation should have the correct content"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_originThreadLink',
        "thee message should have one origin"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_originThreadLink').textContent,
        "#general",
        "the message pending moderation should have correct origin as its linked document"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_checkbox',
        "there should be a moderation checkbox next to the message"
    );
    assert.notOk(
        document.querySelector('.o_Message_checkbox').checked,
        "the moderation checkbox should be unchecked by default"
    );
    // check select all (enabled) / unselect all (disabled) buttons
    assert.containsOnce(
        document.body,
        '.o_widget_Discuss_controlPanelButtonSelectAll',
        "there should be a 'Select All' button in the control panel"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_widget_Discuss_controlPanelButtonSelectAll'),
        'disabled',
        "the 'Select All' button should not be disabled"
    );
    assert.containsOnce(
        document.body,
        '.o_widget_Discuss_controlPanelButtonUnselectAll',
        "there should be a 'Unselect All' button in the control panel"
    );
    assert.hasClass(
        document.querySelector('.o_widget_Discuss_controlPanelButtonUnselectAll'),
        'disabled',
        "the 'Unselect All' button should be disabled"
    );
    // check moderate all buttons (invisible)
    assert.containsN(
        document.body,
        '.o_widget_Discuss_controlPanelButtonModeration',
        3,
        "there should be 3 buttons to moderate selected messages in the control panel"
    );
    assert.containsOnce(
        document.body,
        '.o_widget_Discuss_controlPanelButtonModeration.o-accept',
        "there should one moderate button to accept messages pending moderation"
    );
    assert.isNotVisible(
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-accept'),
        "the moderate button 'Accept' should be invisible by default"
    );
    assert.containsOnce(
        document.body,
        '.o_widget_Discuss_controlPanelButtonModeration.o-reject',
        "there should one moderate button to reject messages pending moderation"
    );
    assert.isNotVisible(
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-reject'),
        "the moderate button 'Reject' should be invisible by default"
    );
    assert.containsOnce(
        document.body,
        '.o_widget_Discuss_controlPanelButtonModeration.o-discard',
        "there should one moderate button to discard messages pending moderation"
    );
    assert.isNotVisible(
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-discard'),
        "the moderate button 'Discard' should be invisible by default"
    );

    // click on message moderation checkbox
    await afterNextRender(() => document.querySelector('.o_Message_checkbox').click());
    assert.ok(
        document.querySelector('.o_Message_checkbox').checked,
        "the moderation checkbox should become checked after click"
    );
    // check select all (disabled) / unselect all buttons (enabled)
    assert.hasClass(
        document.querySelector('.o_widget_Discuss_controlPanelButtonSelectAll'),
        'disabled',
        "the 'Select All' button should be disabled"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_widget_Discuss_controlPanelButtonUnselectAll'),
        'disabled',
        "the 'Unselect All' button should not be disabled"
    );
    // check moderate all buttons updated (visible)
    assert.isVisible(
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-accept'),
        "the moderate button 'Accept' should be visible"
    );
    assert.isVisible(
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-reject'),
        "the moderate button 'Reject' should be visible"
    );
    assert.isVisible(
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-discard'),
        "the moderate button 'Discard' should be visible"
    );

    // test select buttons
    await afterNextRender(() =>
        document.querySelector('.o_widget_Discuss_controlPanelButtonUnselectAll').click()
    );
    assert.notOk(
        document.querySelector('.o_Message_checkbox').checked,
        "the moderation checkbox should become unchecked after click"
    );

    await afterNextRender(() =>
        document.querySelector('.o_widget_Discuss_controlPanelButtonSelectAll').click()
    );
    assert.ok(
        document.querySelector('.o_Message_checkbox').checked,
        "the moderation checkbox should become checked again after click"
    );

    // 2. go to channel 'general'
    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    // check correct message
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should be only one message in general channel"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_checkbox',
        "there should be a moderation checkbox next to the message"
    );
    assert.notOk(
        document.querySelector('.o_Message_checkbox').checked,
        "the moderation checkbox should not be checked here"
    );
    await afterNextRender(() => document.querySelector('.o_Message_checkbox').click());
    // Don't test moderation actions visibility, since it is similar to moderation box.

    // 3. test discard button
    await afterNextRender(() =>
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-discard').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ModerationDiscardDialog',
        "discard dialog should be open"
    );
    // the dialog will be tested separately
    await afterNextRender(() =>
        document.querySelector('.o_ModerationDiscardDialog .o-cancel').click()
    );
    assert.containsNone(
        document.body,
        '.o_ModerationDiscardDialog',
        "discard dialog should be closed"
    );

    // 4. test reject button
    await afterNextRender(() =>
        document.querySelector(`
            .o_widget_Discuss_controlPanelButtonModeration.o-reject
        `).click()
    );
    assert.containsOnce(
        document.body,
        '.o_ModerationRejectDialog',
        "reject dialog should be open"
    );
    // the dialog will be tested separately
    await afterNextRender(() =>
        document.querySelector('.o_ModerationRejectDialog .o-cancel').click()
    );
    assert.containsNone(
        document.body,
        '.o_ModerationRejectDialog',
        "reject dialog should be closed"
    );

    // 5. test accept button
    await afterNextRender(() =>
        document.querySelector('.o_widget_Discuss_controlPanelButtonModeration.o-accept').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should still be only one message in general channel"
    );
    assert.containsNone(
        document.body,
        '.o_Message_checkbox',
        "there should not be a moderation checkbox next to the message"
    );
});

QUnit.test('accept pending moderation message', async function (assert) {
    assert.expect(12);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [20],
    });
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'moderate') {
                assert.step('moderate');
                const messageIDs = args.args[0];
                const decision = args.args[1];
                assert.strictEqual(
                    messageIDs.length,
                    1,
                    "should moderate one message"
                );
                assert.strictEqual(
                    messageIDs[0],
                    100,
                    "should moderate message with ID 100"
                );
                assert.strictEqual(
                    decision,
                    'accept',
                    "should accept the message"
                );
            }
            return this._super(...arguments);
        },
    });

    // 1. go to moderation box
    const moderationBox = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.messaging.moderation.localId
        }"]
    `);
    assert.ok(
        moderationBox,
        "should display the moderation box"
    );

    await afterNextRender(() => moderationBox.click());
    assert.ok(
        document.querySelector(`
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
        `),
        "should display the message to moderate"
    );
    const acceptButton = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
        .o_Message_moderationAction.o-accept
    `);
    assert.ok(acceptButton, "should display the accept button");

    await afterNextRender(() => acceptButton.click());
    assert.verifySteps(['moderate']);
    assert.containsOnce(
        document.body,
        '.o_MessageList_emptyTitle',
        "should now have no message displayed in moderation box"
    );

    // 2. go to channel 'general'
    const channel = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 20 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.ok(
        channel,
        "should display the general channel"
    );

    await afterNextRender(() => channel.click());
    const message = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
    `);
    assert.ok(
        message,
        "should display the accepted message"
    );
    assert.containsNone(
        message,
        '.o_Message_moderationPending',
        "the message should not be pending moderation"
    );
});

QUnit.test('reject pending moderation message (reject with explanation)', async function (assert) {
    assert.expect(23);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [20],
    });
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'moderate') {
                assert.step('moderate');
                const messageIDs = args.args[0];
                const decision = args.args[1];
                const kwargs = args.kwargs;
                assert.strictEqual(
                    messageIDs.length,
                    1,
                    "should moderate one message"
                );
                assert.strictEqual(
                    messageIDs[0],
                    100,
                    "should moderate message with ID 100"
                );
                assert.strictEqual(
                    decision,
                    'reject',
                    "should reject the message"
                );
                assert.strictEqual(
                    kwargs.title,
                    "Message Rejected",
                    "should have correct reject message title"
                );
                assert.strictEqual(
                    kwargs.comment,
                    "Your message was rejected by moderator.",
                    "should have correct reject message body / comment"
                );
            }
            return this._super(...arguments);
        },
    });

    // 1. go to moderation box
    const moderationBox = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.messaging.moderation.localId
        }"]
    `);
    assert.ok(
        moderationBox,
        "should display the moderation box"
    );

    await afterNextRender(() => moderationBox.click());
    const pendingMessage = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
    `);
    assert.ok(
        pendingMessage,
        "should display the message to moderate"
    );
    const rejectButton = pendingMessage.querySelector(':scope .o_Message_moderationAction.o-reject');
    assert.ok(
        rejectButton,
        "should display the reject button"
    );

    await afterNextRender(() => rejectButton.click());
    const dialog = document.querySelector('.o_ModerationRejectDialog');
    assert.ok(
        dialog,
        "a dialog should be prompt to the moderator on click reject"
    );
    assert.strictEqual(
        dialog.querySelector('.modal-title').textContent,
        // TODO FIXME, this should be a proper title "Send explanation to author"
        // see https://github.com/odoo/owl/issues/670
        "[object Object]",
        "dialog should have correct title"
    );

    const messageTitle = dialog.querySelector(':scope .o_ModerationRejectDialog_title');
    assert.ok(
        messageTitle,
        "should have a title for rejecting"
    );
    assert.hasAttrValue(
        messageTitle,
        'placeholder',
        "Subject",
        "title for reject reason should have correct placeholder"
    );
    assert.strictEqual(
        messageTitle.value,
        "Message Rejected",
        "title for reject reason should have correct default value"
    );

    const messageComment = dialog.querySelector(':scope .o_ModerationRejectDialog_comment');
    assert.ok(
        messageComment,
        "should have a comment for rejecting"
    );
    assert.hasAttrValue(
        messageComment,
        'placeholder',
        "Mail Body",
        "comment for reject reason should have correct placeholder"
    );
    assert.strictEqual(
        messageComment.value,
        "Your message was rejected by moderator.",
        "comment for reject reason should have correct default text content"
    );
    const confirmReject = dialog.querySelector(':scope .o-reject');
    assert.ok(
        confirmReject,
        "should have reject button"
    );
    assert.strictEqual(
        confirmReject.textContent,
        "Reject"
    );

    await afterNextRender(() => confirmReject.click());
    assert.verifySteps(['moderate']);
    assert.containsOnce(
        document.body,
        '.o_MessageList_emptyTitle',
        "should now have no message displayed in moderation box"
    );

    // 2. go to channel 'general'
    const channel = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 20 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.ok(
        channel,
        'should display the general channel'
    );

    await afterNextRender(() => channel.click());
    assert.containsNone(
        document.body,
        '.o_Message',
        "should now have no message in channel"
    );
});

QUnit.test('discard pending moderation message (reject without explanation)', async function (assert) {
    assert.expect(16);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [20],
    });
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'moderate') {
                assert.step('moderate');
                const messageIDs = args.args[0];
                const decision = args.args[1];
                assert.strictEqual(messageIDs.length, 1, "should moderate one message");
                assert.strictEqual(messageIDs[0], 100, "should moderate message with ID 100");
                assert.strictEqual(decision, 'discard', "should discard the message");
            }
            return this._super(...arguments);
        },
    });

    // 1. go to moderation box
    const moderationBox = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.messaging.moderation.localId
        }"]
    `);
    assert.ok(
        moderationBox,
        "should display the moderation box"
    );

    await afterNextRender(() => moderationBox.click());
    const pendingMessage = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
    `);
    assert.ok(
        pendingMessage,
        "should display the message to moderate"
    );

    const discardButton = pendingMessage.querySelector(`
        :scope .o_Message_moderationAction.o-discard
    `);
    assert.ok(
        discardButton,
        "should display the discard button"
    );

    await afterNextRender(() => discardButton.click());
    const dialog = document.querySelector('.o_ModerationDiscardDialog');
    assert.ok(
        dialog,
        "a dialog should be prompt to the moderator on click discard"
    );
    assert.strictEqual(
        dialog.querySelector('.modal-title').textContent,
        // TODO FIXME, this should be a proper title "Confirmation"
        // see https://github.com/odoo/owl/issues/670
        "[object Object]",
        "dialog should have correct title"
    );
    assert.strictEqual(
        dialog.textContent,
        "[object Object]×You are going to discard 1 message.Do you confirm the action?DiscardCancel",
        "should warn the user on discard action"
    );

    const confirmDiscard = dialog.querySelector(':scope .o-discard');
    assert.ok(
        confirmDiscard,
        "should have discard button"
    );
    assert.strictEqual(
        confirmDiscard.textContent,
        "Discard"
    );

    await afterNextRender(() => confirmDiscard.click());
    assert.verifySteps(['moderate']);
    assert.containsOnce(
        document.body,
        '.o_MessageList_emptyTitle',
        "should now have no message displayed in moderation box"
    );

    // 2. go to channel 'general'
    const channel = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 20 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.ok(
        channel,
        "should display the general channel"
    );

    await afterNextRender(() => channel.click());
    assert.containsNone(
        document.body,
        '.o_Message',
        "should now have no message in channel"
    );
});

QUnit.test('send message in moderated channel', async function (assert) {
    assert.expect(4);

    const self = this;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    });

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                const message = {
                    id: 100,
                    author_id: [13, 'Someone'],
                    body: args.kwargs.body,
                    channel_ids: [20],
                    message_type: args.kwargs.message_type,
                    model: 'mail.channel',
                    moderation_status: 'pending_moderation',
                    res_id: 20,
                };
                const notificationData = {
                    type: 'author',
                    message: message,
                };
                const notification = [[false, 'res.partner', 13], notificationData];
                self.widget.call('bus_service', 'trigger', 'notification', [notification]);

                return message.id;
            }
            return this._super(...arguments);
        },
    });

    // go to channel 'general'
    const channel = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 20 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.ok(
        channel,
        "should display the general channel"
    );

    await afterNextRender(() => channel.click());
    assert.containsNone(
        document.body,
        '.o_Message',
        "should have no message in channel"
    );

    // post a message
    await afterNextRender(() => {
        const textInput = document.querySelector('.o_ComposerTextInput_textarea');
        textInput.focus();
        document.execCommand('insertText', false, "Some Text");
    });
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());
    const messagePending = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
        .o_Message_moderationPending
    `);
    assert.ok(
        messagePending,
        "should display the pending message with pending info"
    );
    assert.hasClass(
        messagePending,
        'o-author',
        "the message should be pending moderation as author"
    );
});

QUnit.test('sent message accepted in moderated channel', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    });
    this.data['mail.message'].records = [{
        author_id: [13, "Someone"],
        body: "<p>test</p>",
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await this.start();

    const channel = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 20 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.ok(
        channel,
        "should display the general channel"
    );

    await afterNextRender(() => channel.click());
    const messagePending = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
        .o_Message_moderationPending
    `);
    assert.ok(
        messagePending,
        "should display the pending message with pending info"
    );
    assert.hasClass(
        messagePending,
        'o-author',
        "the message should be pending moderation as author"
    );

    // simulate accepted message
    await afterNextRender(() => {
        const messageData = {
            author_id: [13, "Someone"],
            body: "<p>test</p>",
            channel_ids: [20],
            id: 100,
            model: 'mail.channel',
            moderation_status: 'accepted',
            res_id: 20,
        };
        const notification = [[false, 'mail.channel', 20], messageData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });

    // check message is accepted
    const message = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
    `);
    assert.ok(
        message,
        "should still display the message"
    );
    assert.containsNone(
        message,
        '.o_Message_moderationPending',
        "the message should not be in pending moderation anymore"
    );
});

QUnit.test('sent message rejected in moderated channel', async function (assert) {
    assert.expect(4);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    });
    this.data['mail.message'].records = [{
        author_id: [13, "Someone"],
        body: "<p>test</p>",
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await this.start();

    const channel = document.querySelector(`
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 20 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.ok(
        channel,
        "should display the general channel"
    );

    await afterNextRender(() => channel.click());
    const messagePending = document.querySelector(`
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
        .o_Message_moderationPending
    `);
    assert.ok(
        messagePending,
        "should display the pending message with pending info"
    );
    assert.hasClass(
        messagePending,
        'o-author',
        "the message should be pending moderation as author"
    );

    // simulate reject from moderator
    await afterNextRender(() => {
        const notifData = {
            type: 'deletion',
            message_ids: [100],
        };
        const notification = [[false, 'res.partner', 13], notifData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    // check no message
    assert.containsNone(
        document.body,
        '.o_Message',
        "message should be removed from channel after reject"
    );
});

QUnit.test('as moderator, pending moderation message accessibility', async function (assert) {
    // pending moderation message should appear in moderation box and in origin thread
    assert.expect(3);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [20],
    });
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        channel_ids: [20],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await this.start();

    const thread = this.env.models['mail.thread'].find(thread => thread.id === 20 && thread.model === 'mail.channel');
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.moderation.localId
            }"]
        `),
        "should display the moderation box in the sidebar"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${thread.localId}"]
        `).click()
    );
    const message = this.env.models['mail.message'].find(message => message.id === 100);
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${message.localId}"]`,
        "the pending moderation message should be in the channel"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.moderation.localId
            }"]
        `).click()
    );
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${message.localId}"]`,
        "the pending moderation message should be in moderation box"
    );
});

QUnit.test('as author, pending moderation message should appear in origin thread', async function (assert) {
    assert.expect(1);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    });
    await this.start();
    const thread = this.env.models['mail.thread'].find(thread => thread.id === 20 && thread.model === 'mail.channel');
    this.data['mail.message'].records = [{
        author_id: [this.env.session.partner_id, "Me"],
        body: "<p>test</p>",
        channel_ids: [], // server do NOT return channel_id of the message
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 20,
    }];

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${thread.localId}"]
        `).click()
    );
    const message = this.env.models['mail.message'].find(message => message.id === 100);
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${message.localId}"]`,
        "the pending moderation message should be in the channel"
    );
});

QUnit.test('new pending moderation message posted by me', async function (assert) {
    // message should appear in origin thread
    assert.expect(1);

    const self = this;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                // simulate receiving the message
                const message = {
                    author_id: [self.env.session.partner_id, "Me"],
                    body: args.kwargs.body,
                    channel_ids: [], // server do NOT return channel_id of the message if pending moderation
                    moderation_status: 'pending_moderation',
                    id: 2,
                    message_type: args.kwargs.message_type,
                    model: 'mail.channel',
                    subtype_xmlid: args.kwargs.subtype_xmlid,
                    record_name: 'General',
                    res_id: 20,
                };
                const notifications = [[
                    ['my-db', 'res.partner', self.env.session.partner_id],
                    { type: 'author', message },
                ]];
                self.widget.call('bus_service', 'trigger', 'notification', notifications);
            }
            return this._super(...arguments);
        }
    });
    const thread = this.env.models['mail.thread'].find(thread => thread.id === 20 && thread.model === 'mail.channel');
    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${thread.localId}"]
        `).click()
    );

    await afterNextRender(() => {
        document.querySelector('.o_ComposerTextInput').focus();
        document.execCommand('insertText', false, "Moderated test");
    });
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
    const message = this.env.models['mail.message'].find(message => message.id === 2);
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${message.localId}"]`,
        "the pending moderation message should be in the channel"
    );
});

QUnit.test('new pending moderation message posted by someone else when moderator', async function (assert) {
    // the message should appear in origin thread and moderation box if I moderate it
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                id: 20,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_channel_ids: [20],
    });
    await this.start();
    const thread = this.env.models['mail.thread'].find(thread => thread.id === 20 && thread.model === 'mail.channel');
    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${thread.localId}"]
        `).click()
    );

    // simulate receiving the message
    const messageData = {
        author_id: [10, "Don Diego de la Vega"],
        body: "hoy !",
        channel_ids: [], // server do NOT return channel_id of the message if pending moderation
        moderation_status: 'pending_moderation',
        id: 1,
        model: 'mail.channel',
        record_name: 'General',
        res_id: 20,
    };
    await afterNextRender(() => {
        const notifications = [[
            ['my-db', 'res.partner', this.env.session.partner_id],
            { type: 'moderator', message: messageData },
        ]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
    });
    const message = this.env.models['mail.message'].find(message => message.id === 1);
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${message.localId}"]`,
        "the pending moderation message should be in the channel"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.moderation.localId
            }"]
        `).click()
    );
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${message.localId}"]`,
        "the pending moderation message should be in moderation box"
    );
});

});
});
});

});
