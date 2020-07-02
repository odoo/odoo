odoo.define('mail/static/src/components/discuss/tests/discuss_inbox_tests.js', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    nextAnimationFrame,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');


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

});
});
});

});
