odoo.define('mail/static/src/components/composer/composer_tests.js', function (require) {
'use strict';

const components = {
    Composer: require('mail/static/src/components/composer/composer.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    dragenterFiles,
    dropFiles,
    inputFiles,
    nextAnimationFrame,
    pasteFiles,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const { file: { createFile } } = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer', {}, function () {
QUnit.module('composer_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createComposerComponent = async (composer, otherProps) => {
            const ComposerComponent = components.Composer;
            ComposerComponent.env = this.env;
            this.component = new ComposerComponent(null, Object.assign({
                composerLocalId: composer.localId,
            }, otherProps));
            await afterNextRender(() => this.component.mount(this.widget.el));
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    async afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.Composer.env;
    },
});

QUnit.test('composer text input: basic rendering when posting a message', async function (assert) {
    assert.expect(5);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        composer: [['create', { isLog: false }]],
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);
    assert.strictEqual(
        document.querySelectorAll('.o_Composer').length,
        1,
        "should have composer in discuss thread"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Composer_textInput').length,
        1,
        "should have text input inside discuss thread composer"
    );
    assert.ok(
        document.querySelector('.o_Composer_textInput').classList.contains('o_ComposerTextInput'),
        "composer text input of composer should be a ComposerTextIput component"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ComposerTextInput_textarea`).length,
        1,
        "should have editable part inside composer text input"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).placeholder,
        "Send a message to followers...",
        "should have 'Send a message to followers...' as placeholder composer text input"
    );
});

QUnit.test('composer text input: basic rendering when logging note', async function (assert) {
    assert.expect(5);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        composer: [['create', { isLog: true }]],
        id: 20,
        model: 'res.partner',
    });
    await this.createComposerComponent(thread.composer);
    assert.strictEqual(
        document.querySelectorAll('.o_Composer').length,
        1,
        "should have composer in discuss thread"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Composer_textInput').length,
        1,
        "should have text input inside discuss thread composer"
    );
    assert.ok(
        document.querySelector('.o_Composer_textInput').classList.contains('o_ComposerTextInput'),
        "composer text input of composer should be a ComposerTextIput component"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ComposerTextInput_textarea`).length,
        1,
        "should have editable part inside composer text input"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).placeholder,
        "Log an internal note...",
        "should have 'Log an internal note...' as placeholder in composer text input if composer is log"
    );
});

QUnit.test('composer text input: basic rendering when linked thread is a mail.channel', async function (assert) {
    assert.expect(5);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 20,
        model: 'mail.channel',
    });
    await this.createComposerComponent(thread.composer);
    assert.strictEqual(
        document.querySelectorAll('.o_Composer').length,
        1,
        "should have composer in discuss thread"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Composer_textInput').length,
        1,
        "should have text input inside discuss thread composer"
    );
    assert.ok(
        document.querySelector('.o_Composer_textInput').classList.contains('o_ComposerTextInput'),
        "composer text input of composer should be a ComposerTextIput component"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ComposerTextInput_textarea`).length,
        1,
        "should have editable part inside composer text input"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).placeholder,
        "Write something...",
        "should have 'Write something...' as placeholder in composer text input if composer is for a 'mail.channel'"
    );
});

QUnit.test('add an emoji', async function (assert) {
    assert.expect(1);

    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonEmojis').click()
    );
    await afterNextRender(() =>
        document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "😊",
        "emoji should be inserted in the composer text input"
    );
    // ensure popover is closed
    await nextAnimationFrame();
    await nextAnimationFrame();
    await nextAnimationFrame();
});

QUnit.test('add an emoji after some text', async function (assert) {
    assert.expect(2);

    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Blabla");
    });
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "Blabla",
        "composer text input should have text only initially"
    );

    await afterNextRender(() => document.querySelector('.o_Composer_buttonEmojis').click());
    await afterNextRender(() =>
        document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "Blabla😊",
        "emoji should be inserted after the text"
    );
    // ensure popover is closed
    await nextAnimationFrame();
    await nextAnimationFrame();
    await nextAnimationFrame();
});

QUnit.test('add emoji replaces (keyboard) text selection', async function (assert) {
    assert.expect(2);

    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);
    const composerTextInputTextArea = document.querySelector(`.o_ComposerTextInput_textarea`);
    await afterNextRender(() => {
        composerTextInputTextArea.focus();
        document.execCommand('insertText', false, "Blabla");
    });
    assert.strictEqual(
        composerTextInputTextArea.value,
        "Blabla",
        "composer text input should have text only initially"
    );

    // simulate selection of all the content by keyboard
    composerTextInputTextArea.setSelectionRange(0, composerTextInputTextArea.value.length);

    // select emoji
    await afterNextRender(() => document.querySelector('.o_Composer_buttonEmojis').click());
    await afterNextRender(() =>
        document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "😊",
        "whole text selection should have been replaced by emoji"
    );
    // ensure popover is closed
    await nextAnimationFrame();
    await nextAnimationFrame();
    await nextAnimationFrame();
});

QUnit.test('display partner mention suggestions on typing "@"', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records = [{
        email: "testpartnert@odoo.com",
        id: 11,
        name: "TestPartner",
    }];
    this.data['res.users'].records = [{
        partner_id: 11,
    }];
    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);

    assert.containsNone(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestions list should not be present"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "@");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.hasClass(
        document.querySelector('.o_ComposerTextInput_mentionDropdownPropositionList'),
        'show',
        "should display mention suggestions on typing '@'"
    );
});

QUnit.test('mention a partner', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records = [{
        email: "testpartnert@odoo.com",
        id: 11,
        name: "TestPartner",
    }];
    this.data['res.users'].records = [{
        partner_id: 11,
    }];
    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);

    assert.containsNone(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "@");
    });
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_PartnerMentionSuggestion',
        "should have a mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_PartnerMentionSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "@TestPartner ",
        "text content of composer should have mentioned partner + additional whitespace afterwards"
    );
});

QUnit.test('mention a partner after some text', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records = [{
        email: "testpartnert@odoo.com",
        id: 11,
        name: "TestPartner",
    }];
    this.data['res.users'].records = [{
        partner_id: 11,
    }];
    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);

    assert.containsNone(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    await afterNextRender(() =>
        document.execCommand('insertText', false, "bluhbluh ")
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "bluhbluh ",
        "text content of composer should have content"
    );
    await afterNextRender(() =>
        document.execCommand('insertText', false, "@")
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_PartnerMentionSuggestion',
        "should have a mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_PartnerMentionSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "bluhbluh @TestPartner ",
        "text content of composer should have previous content + mentioned partner + additional whitespace afterwards"
    );
});

QUnit.test('add an emoji after a partner mention', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records = [{
        email: "testpartnert@odoo.com",
        id: 11,
        name: "TestPartner",
    }];
    this.data['res.users'].records = [{
        partner_id: 11,
    }];
    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);

    assert.containsNone(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "@");
    });
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_PartnerMentionSuggestion',
        "should have a mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_PartnerMentionSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "@TestPartner ",
        "text content of composer should have previous content + mentioned partner + additional whitespace afterwards"
    );

    // select emoji
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonEmojis').click()
    );
    await afterNextRender(() =>
        document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "@TestPartner 😊",
        "text content of composer should have previous mention and selected emoji just after"
    );
    // ensure popover is closed
    await nextAnimationFrame();
});

QUnit.test('composer: add an attachment', async function (assert) {
    assert.expect(2);

    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer, { attachmentsDetailsMode: 'card' });
    const file = await createFile({
        content: 'hello, world',
        contentType: 'text/plain',
        name: 'text.txt',
    });
    await afterNextRender(() =>
        inputFiles(
            document.querySelector('.o_FileUploader_input'),
            [file]
        )
    );
    assert.ok(
        document.querySelector('.o_Composer_attachmentList'),
        "should have an attachment list"
    );
    assert.ok(
        document.querySelector(`.o_Composer .o_Attachment`),
        "should have an attachment"
    );
});

QUnit.test('composer: drop attachments', async function (assert) {
    assert.expect(4);

    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);
    const files = [
        await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        }),
        await createFile({
            content: 'hello, worlduh',
            contentType: 'text/plain',
            name: 'text2.txt',
        }),
    ];
    await afterNextRender(() => dragenterFiles(document.querySelector('.o_Composer')));
    assert.ok(
        document.querySelector('.o_Composer_dropZone'),
        "should have a drop zone"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        0,
        "should have no attachment before files are dropped"
    );

    await afterNextRender(() =>
        dropFiles(
            document.querySelector('.o_Composer_dropZone'),
            files
        )
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        2,
        "should have 2 attachments in the composer after files dropped"
    );

    await afterNextRender(() => dragenterFiles(document.querySelector('.o_Composer')));
    await afterNextRender(async () =>
        dropFiles(
            document.querySelector('.o_Composer_dropZone'),
            [
                await createFile({
                    content: 'hello, world',
                    contentType: 'text/plain',
                    name: 'text3.txt',
                })
            ]
        )
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        3,
        "should have 3 attachments in the box after files dropped"
    );
});

QUnit.test('composer: paste attachments', async function (assert) {
    assert.expect(2);

    await this.start();
    const composer = this.env.models['mail.composer'].create();
    await this.createComposerComponent(composer);
    const files = [
        await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        })
    ];
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        0,
        "should not have any attachment in the composer before paste"
    );

    await afterNextRender(() =>
        pasteFiles(document.querySelector('.o_ComposerTextInput'), files)
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        1,
        "should have 1 attachment in the composer after paste"
    );
});

QUnit.test('composer text input cleared on message post', async function (assert) {
    assert.expect(4);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_pinned: true,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                assert.step('message_post');
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createComposerComponent(thread.composer);
    // Type message
    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    document.execCommand('insertText', false, "test message");
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "test message",
        "should have inserted text content in editable"
    );

    // Send message
    await afterNextRender(() =>
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }))
    );
    assert.verifySteps(['message_post']);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "should have no content in composer input after posting message"
    );
});

QUnit.test('composer with thread typing notification status', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_pinned: true,
                name: "General",
            }],
        },
    });
    await this.start();
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createComposerComponent(thread.composer, { hasThreadTyping: true });

    assert.containsOnce(
        document.body,
        '.o_Composer_threadTextualTypingStatus',
        "Composer should have a thread textual typing status bar"
    );
    assert.strictEqual(
        document.body.querySelector('.o_Composer_threadTextualTypingStatus').textContent,
        "",
        "By default, thread textual typing status bar should be empty"
    );
});

QUnit.test('current partner notify is typing to other thread members', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_pinned: true,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createComposerComponent(thread.composer, { hasThreadTyping: true });

    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    document.execCommand('insertText', false, "a");
    document.querySelector(`.o_ComposerTextInput_textarea`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'a' }));

    assert.verifySteps(
        ['notify_typing:true'],
        "should have notified current partner typing status"
    );
});

QUnit.test('current partner is typing should not translate on textual typing status', async function (assert) {
    assert.expect(3);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_pinned: true,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
        hasTimeControl: true,
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createComposerComponent(thread.composer, { hasThreadTyping: true });

    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    document.execCommand('insertText', false, "a");
    document.querySelector(`.o_ComposerTextInput_textarea`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'a' }));

    assert.verifySteps(
        ['notify_typing:true'],
        "should have notified current partner typing status"
    );

    await nextAnimationFrame();
    assert.strictEqual(
        document.body.querySelector('.o_Composer_threadTextualTypingStatus').textContent,
        "",
        "Thread textual typing status bar should not display current partner is typing"
    );
});

QUnit.test('current partner notify no longer is typing to thread members after 5 seconds inactivity', async function (assert) {
    assert.expect(4);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_pinned: true,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
        hasTimeControl: true,
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createComposerComponent(thread.composer, { hasThreadTyping: true });

    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    document.execCommand('insertText', false, "a");
    document.querySelector(`.o_ComposerTextInput_textarea`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'a' }));

    assert.verifySteps(
        ['notify_typing:true'],
        "should have notified current partner is typing"
    );

    await this.env.testUtils.advanceTime(5 * 1000);
    assert.verifySteps(
        ['notify_typing:false'],
        "should have notified current partner no longer is typing (inactive for 5 seconds)"
    );
});

QUnit.test('current partner notify is typing again to other members every 50s of long continuous typing', async function (assert) {
    assert.expect(4);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_pinned: true,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
        hasTimeControl: true,
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createComposerComponent(thread.composer, { hasThreadTyping: true });

    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    document.execCommand('insertText', false, "a");
    document.querySelector(`.o_ComposerTextInput_textarea`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'a' }));
    assert.verifySteps(
        ['notify_typing:true'],
        "should have notified current partner is typing"
    );

    // simulate current partner typing a character every 2.5 seconds for 50 seconds straight.
    let totalTimeElapsed = 0;
    const elapseTickTime = 2.5 * 1000;
    while (totalTimeElapsed < 50 * 1000) {
        document.execCommand('insertText', false, "a");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'a' }));
        totalTimeElapsed += elapseTickTime;
        await this.env.testUtils.advanceTime(elapseTickTime);
    }

    assert.verifySteps(
        ['notify_typing:true'],
        "should have notified current partner is still typing after 50s of straight typing"
    );
});

});
});
});

});
