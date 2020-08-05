odoo.define('mail/static/src/components/discuss/tests/discuss_inbox_tests.js', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    nextAnimationFrame,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const Bus = require('web.Bus');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_inbox_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.start = async params => {
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

QUnit.test('reply: discard on pressing escape', async function (assert) {
    assert.expect(9);

    this.data['res.partner'].records = [{
        email: "testpartnert@odoo.com",
        id: 11,
        name: "TestPartner",
    }];
    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        message_type: 'comment',
        needaction: true,
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: 'Refactoring',
        res_id: 20,
    }];
    await this.start();
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message_commandReply').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_Composer_buttonEmojis`).click()
    );
    assert.containsOnce(
        document.body,
        '.o_EmojisPopover',
        "emojis popover should be opened after click on emojis button"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_Composer_buttonEmojis`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_EmojisPopover',
        "emojis popover should be closed after pressing escape on emojis button"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be opened after pressing escape on emojis button"
    );

    await afterNextRender(() => {
        document.execCommand('insertText', false, "@");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestion should be opened after typing @"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ComposerTextInput_textarea`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestion should be closed after pressing escape on mention suggestion"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be opened after pressing escape on mention suggestion"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ComposerTextInput_textarea`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after pressing escape if there was no other priority escape handler"
    );
});

QUnit.test('reply: discard on discard button click', async function (assert) {
    assert.expect(4);

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        message_type: 'comment',
        needaction: true,
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: "Refactoring",
        res_id: 20,
    }];
    await this.start();
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message_commandReply').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer_buttonDiscard',
        "composer should have a discard button"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_Composer_buttonDiscard`).click()
    );
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after clicking on discard"
    );
});

QUnit.test('reply: discard on reply button toggle', async function (assert) {
    assert.expect(3);

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        message_type: 'comment',
        needaction: true,
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: "Refactoring",
        res_id: 20,
    }];
    await this.start();
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message_commandReply').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_Message_commandReply`).click()
    );
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after clicking on reply button again"
    );
});

QUnit.test('reply: discard on click away', async function (assert) {
    assert.expect(7);

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        message_type: 'comment',
        needaction: true,
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: "Refactoring",
        res_id: 20,
    }];
    await this.start();
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message_commandReply').click()
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "should have composer after clicking on reply to message"
    );

    document.querySelector(`.o_ComposerTextInput_textarea`).click();
    await nextAnimationFrame(); // wait just in case, but nothing is supposed to happen
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be there after clicking inside itself"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_Composer_buttonEmojis`).click()
    );
    assert.containsOnce(
        document.body,
        '.o_EmojisPopover',
        "emojis popover should be opened after clicking on emojis button"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_EmojisPopover_emoji`).click();
    });
    assert.containsNone(
        document.body,
        '.o_EmojisPopover',
        "emojis popover should be closed after selecting an emoji"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer',
        "reply composer should still be there after selecting an emoji (even though it is technically a click away, it should be considered inside)"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_Message`).click()
    );
    assert.containsNone(
        document.body,
        '.o_Composer',
        "reply composer should be closed after clicking away"
    );
});

QUnit.test('"reply to" composer should log note if message replied to is a note', async function (assert) {
    assert.expect(6);

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        is_discussion: false,
        is_notification: false,
        message_type: 'comment',
        needaction: true,
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: "Refactoring",
        res_id: 20,
    }];

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.kwargs.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.kwargs.subtype_xmlid,
                    "mail.mt_note",
                    "should set subtype_xmlid as 'note'"
                );
            }
            return this._super(...arguments);
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message_commandReply').click()
    );
    assert.strictEqual(
        document.querySelector('.o_Composer_buttonSend').textContent.trim(),
        "Log",
        "Send button text should be 'Log'"
    );

    await afterNextRender(() => {
        document.execCommand('insertText', false, "Test");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    });
    assert.verifySteps(['message_post']);
});

QUnit.test('"reply to" composer should send message if message replied to is not a note', async function (assert) {
    assert.expect(6);

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        is_discussion: true,
        is_notification: false,
        message_type: 'comment',
        needaction: true,
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: "Refactoring",
        res_id: 20,
    }];

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.kwargs.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.kwargs.subtype_xmlid,
                    "mail.mt_comment",
                    "should set subtype_xmlid as 'comment'"
                );
            }
            return this._super(...arguments);
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message_commandReply').click()
    );
    assert.strictEqual(
        document.querySelector('.o_Composer_buttonSend').textContent.trim(),
        "Send",
        "Send button text should be 'Send'"
    );

    await afterNextRender(() => {
        document.execCommand('insertText', false, "Test");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    });
    assert.verifySteps(['message_post']);
});

QUnit.test('error notifications should not be shown in inbox', async function (assert) {
    assert.expect(3);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_pinned: true,
                name: "General",
            }],
        },
        needaction_inbox_counter: 1,
    });
    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        message_type: 'comment',
        model: 'mail.channel',
        needaction: true,
        needaction_partner_ids: [3],
        notifications: [{
            id: 11,
            notification_status: 'exception',
            notification_type: 'email',
        }],
        res_id: 20,
    }];
    await this.start();
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_originThreadLink',
        "should display origin thread link"
    );
    assert.containsNone(
        document.body,
        '.o_Message_notificationIcon',
        "should not display any notification icon in inbox"
    );
});

QUnit.test('show subject of message in inbox', async function (assert) {
    assert.expect(3);

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        is_discussion: false,
        is_notification: false,
        message_type: 'comment',
        needaction: true,
        needaction_partner_ids: [3],
        model: 'mail.channel',
        res_id: 20,
        subject: "Salutations, voyageur",
    }];

    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_subject',
        "should display subject of the message"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_subject').textContent,
        "Subject: Salutations, voyageur",
        "Subject of the message should be 'Salutations, voyageur'"
    );
});

QUnit.test('show subject of message in history', async function (assert) {
    assert.expect(3);

    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        history_partner_ids: [3],
        id: 100,
        message_type: 'comment',
        model: 'project.task',
        record_name: "Refactoring",
        res_id: 20,
        subject: "Salutations, voyageur",
    }];

    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.box_history',
            },
        },
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_subject',
        "should display subject of the message"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_subject').textContent,
        "Subject: Salutations, voyageur",
        "Subject of the message should be 'Salutations, voyageur'"
    );
});

QUnit.test('click on (non-channel/non-partner) origin thread link should redirect to form view', async function (assert) {
    assert.expect(9);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        // Callback of doing an action (action manager).
        // Expected to be called on click on origin thread link,
        // which redirects to form view of record related to origin thread
        assert.step('do-action');
        assert.strictEqual(
            payload.action.type,
            'ir.actions.act_window',
            "action should open a view"
        );
        assert.deepEqual(
            payload.action.views,
            [[false, 'form']],
            "action should open form view"
        );
        assert.strictEqual(
            payload.action.res_model,
            'some.model',
            "action should open view with model 'some.model' (model of message origin thread)"
        );
        assert.strictEqual(
            payload.action.res_id,
            10,
            "action should open view with id 10 (id of message origin thread)"
        );
    });
    Object.assign(this.data.initMessaging, {
        needaction_inbox_counter: 1,
    });
    this.data['mail.message'].records = [{
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        message_type: 'comment',
        model: 'some.model',
        needaction: true,
        needaction_partner_ids: [3],
        record_name: "Some record",
        res_id: 10,
    }];
    await this.start({
        env: {
            bus,
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a single message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_originThreadLink',
        "should display origin thread link"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_originThreadLink').textContent,
        "Some record",
        "origin thread link should display record name"
    );

    document.querySelector('.o_Message_originThreadLink').click();
    assert.verifySteps(['do-action'], "should have made an action on click on origin thread (to open form view)");
});

});
});
});

});
