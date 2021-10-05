/** @odoo-module **/

import { insertAndReplace } from '@mail/model/model_field_command';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    dragenterFiles,
    dropFiles,
    nextAnimationFrame,
    pasteFiles,
    start,
} from '@mail/utils/test_utils';

import {
    file,
    makeTestPromise,
} from 'web.test_utils';

const { createFile, inputFiles } = file;

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer', {}, function () {
QUnit.module('composer_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
            const { afterEvent, components, env, widget } = res;
            this.afterEvent = afterEvent;
            this.components = components;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('composer text input: basic rendering when posting a message', async function (assert) {
    assert.expect(5);

    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        composer: insertAndReplace({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await createComposerComponent(thread.composer);
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

    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        composer: insertAndReplace({ isLog: true }),
        id: 20,
        model: 'res.partner',
    });
    await createComposerComponent(thread.composer);
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
    assert.expect(4);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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
});

QUnit.test('composer text input placeholder should contain channel name when thread does not have specific correspondent', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        name: 'General',
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).placeholder,
        "Message #General...",
        "should have 'Message #General...' as placeholder for composer text input when thread does not have specific correspondent"
    );
});

QUnit.test('composer text input placeholder should contain correspondent name when thread has exactly one correspondent', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ id: 7, name: 'Marc Demo' });
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 20,
        members: [this.data.currentPartnerId, 7],
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).placeholder,
        "Message Marc Demo...",
        "should have 'Message Marc Demo...' as placeholder for composer text input when thread has exactly one correspondent"
    );
});

QUnit.test('add an emoji', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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

QUnit.test('display canned response suggestions on typing ":"', async function (assert) {
    assert.expect(2);

    this.data['mail.shortcode'].records.push({
        id: 11,
        source: "hello",
        substitution: "Hello! How are you?",
    });

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
        "Canned responses suggestions list should not be present"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, ":");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionList_list'),
        'show',
        "should display canned response suggestions on typing ':'"
    );
});

QUnit.test('use a canned response', async function (assert) {
    assert.expect(4);

    this.data['mail.shortcode'].records.push({
        id: 11,
        source: "hello",
        substitution: "Hello! How are you?",
    });

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
        "canned response suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, ":");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a canned response suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "Hello! How are you? ",
        "text content of composer should have canned response + additional whitespace afterwards"
    );
});

QUnit.test('use a canned response some text', async function (assert) {
    assert.expect(5);

    this.data['mail.shortcode'].records.push({
        id: 11,
        source: "hello",
        substitution: "Hello! How are you?",
    });

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
        "canned response suggestions list should not be present"
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
    await afterNextRender(() => {
        document.execCommand('insertText', false, ":");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a canned response suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "bluhbluh Hello! How are you? ",
        "text content of composer should have previous content + canned response substitution + additional whitespace afterwards"
    );
});

QUnit.test('add an emoji after a canned response', async function (assert) {
    assert.expect(5);

    this.data['mail.shortcode'].records.push({
        id: 11,
        source: "hello",
        substitution: "Hello! How are you?",
    });

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
        "canned response suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, ":");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a canned response suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "Hello! How are you? ",
        "text content of composer should have previous content + canned response substitution + additional whitespace afterwards"
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
        "Hello! How are you? 😊",
        "text content of composer should have previous canned response substitution and selected emoji just after"
    );
    // ensure popover is closed
    await nextAnimationFrame();
});

QUnit.test('display channel mention suggestions on typing "#"', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General",
        public: "groups",
    });

    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
        "channel mention suggestions list should not be present"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionList_list'),
        'show',
        "should display channel mention suggestions on typing '#'"
    );
});

QUnit.test('mention a channel', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General",
        public: "groups",
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
        "channel mention suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a channel mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "#General ",
        "text content of composer should have mentioned channel + additional whitespace afterwards"
    );
});

QUnit.test('mention a channel after some text', async function (assert) {
    assert.expect(5);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General",
        public: "groups",
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
        "channel mention suggestions list should not be present"
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
    await afterNextRender(() => {
        document.execCommand('insertText', false, "#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a channel mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "bluhbluh #General ",
        "text content of composer should have previous content + mentioned channel + additional whitespace afterwards"
    );
});

QUnit.test('add an emoji after a channel mention', async function (assert) {
    assert.expect(5);

    this.data['mail.channel'].records.push({
        id: 7,
        name: "General",
        public: "groups",
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 7,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
        "mention suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "#");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a channel mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "#General ",
        "text content of composer should have previous content + mentioned channel + additional whitespace afterwards"
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
        "#General 😊",
        "text content of composer should have previous channel mention and selected emoji just after"
    );
    // ensure popover is closed
    await nextAnimationFrame();
});

QUnit.test('display command suggestions on typing "/"', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ channel_type: 'channel', id: 20 });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
        "command suggestions list should not be present"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "/");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionList_list'),
        'show',
        "should display command suggestions on typing '/'"
    );
});

QUnit.test('do not send typing notification on typing "/" command', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, { hasThreadTyping: true });

    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "/");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.verifySteps([], "No rpc done");
});

QUnit.test('do not send typing notification on typing after selecting suggestion from "/" command', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, { hasThreadTyping: true });

    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "/");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, " is user?");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.verifySteps([], "No rpc done");
});

QUnit.test('use a command for a specific channel type', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({ channel_type: 'channel', id: 20 });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
        "command suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "/");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "/who ",
        "text content of composer should have used command + additional whitespace afterwards"
    );
});

QUnit.test('command suggestion should only open if command is the first character', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({ channel_type: 'channel', id: 20 });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
        "command suggestions list should not be present"
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
    await afterNextRender(() => {
        document.execCommand('insertText', false, "/");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
        "should not have a command suggestion"
    );
});

QUnit.test('add an emoji after a command', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({ channel_type: 'channel', id: 20 });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
        "command suggestions list should not be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "text content of composer should be empty initially"
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "/");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "/who ",
        "text content of composer should have previous content + used command + additional whitespace afterwards"
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
        "/who 😊",
        "text content of composer should have previous command and selected emoji just after"
    );
    // ensure popover is closed
    await nextAnimationFrame();
});

QUnit.test('display partner mention suggestions on typing "@"', async function (assert) {
    assert.expect(3);

    this.data['res.partner'].records.push({
        id: 11,
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    this.data['res.partner'].records.push({
        id: 12,
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    this.data['res.users'].records.push({
        partner_id: 11,
    });

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
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
        document.querySelector('.o_ComposerSuggestionList_list'),
        'show',
        "should display mention suggestions on typing '@'"
    );
    assert.containsOnce(
        document.body,
        '.dropdown-divider',
        "should have a separator"
    );
});

QUnit.test('mention a partner', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records.push({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
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
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
        document.execCommand('insertText', false, "T");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
        document.execCommand('insertText', false, "e");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "@TestPartner ",
        "text content of composer should have mentioned partner + additional whitespace afterwards"
    );
});

QUnit.test('mention a partner after some text', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records.push({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
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
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "@");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
        document.execCommand('insertText', false, "T");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
        document.execCommand('insertText', false, "e");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value.replace(/\s/, " "),
        "bluhbluh @TestPartner ",
        "text content of composer should have previous content + mentioned partner + additional whitespace afterwards"
    );
});

QUnit.test('add an emoji after a partner mention', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records.push({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

    assert.containsNone(
        document.body,
        '.o_ComposerSuggestion',
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
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
        document.execCommand('insertText', false, "T");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
        document.execCommand('insertText', false, "e");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "should have a mention suggestion"
    );
    await afterNextRender(() =>
        document.querySelector('.o_ComposerSuggestion').click()
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

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);

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
        document.querySelector(`.o_Composer .o_AttachmentCard`),
        "should have an attachment"
    );
});

QUnit.test('composer: drop attachments', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`).length,
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
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`).length,
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
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`).length,
        3,
        "should have 3 attachments in the box after files dropped"
    );
});

QUnit.test('composer: paste attachments', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    const files = [
        await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        })
    ];
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`).length,
        0,
        "should not have any attachment in the composer before paste"
    );

    await afterNextRender(() =>
        pasteFiles(document.querySelector('.o_ComposerTextInput'), files)
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`).length,
        1,
        "should have 1 attachment in the composer after paste"
    );
});

QUnit.test('send message when enter is pressed while holding ctrl key (this shortcut is available)', async function (assert) {
    // Note that test doesn't assert ENTER makes no newline, because this
    // default browser cannot be simulated with just dispatching
    // programmatically crafted events...
    assert.expect(5);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, {
        textInputSendShortcuts: ['ctrl-enter'],
    });
    // Type message
    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    document.execCommand('insertText', false, "test message");
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "test message",
        "should have inserted text content in editable"
    );

    await afterNextRender(() => {
        const enterEvent = new window.KeyboardEvent('keydown', { key: 'Enter' });
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(enterEvent);
    });
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "test message",
        "should have inserted text content in editable as message has not been posted"
    );

    // Send message with ctrl+enter
    await afterNextRender(() =>
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown', { ctrlKey: true, key: 'Enter' }))
    );
    assert.verifySteps(['message_post']);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "should have no content in composer input as message has been posted"
    );
});

QUnit.test('send message when enter is pressed while holding meta key (this shortcut is available)', async function (assert) {
    // Note that test doesn't assert ENTER makes no newline, because this
    // default browser cannot be simulated with just dispatching
    // programmatically crafted events...
    assert.expect(5);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, {
        textInputSendShortcuts: ['meta-enter'],
    });
    // Type message
    document.querySelector(`.o_ComposerTextInput_textarea`).focus();
    document.execCommand('insertText', false, "test message");
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "test message",
        "should have inserted text content in editable"
    );

    await afterNextRender(() => {
        const enterEvent = new window.KeyboardEvent('keydown', { key: 'Enter' });
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(enterEvent);
    });
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "test message",
        "should have inserted text content in editable as message has not been posted"
    );

    // Send message with meta+enter
    await afterNextRender(() =>
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter', metaKey: true }))
    );
    assert.verifySteps(['message_post']);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "should have no content in composer input as message has been posted"
    );
});

QUnit.test('composer text input cleared on message post', async function (assert) {
    assert.expect(4);

    // channel that is expected to be rendered
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    // Type message
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "test message");
    });
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "test message",
        "should have inserted text content in editable"
    );

    // Send message
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
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

    // channel that is expected to be rendered
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, { hasThreadTyping: true });

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

    // channel that is expected to be rendered
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, { hasThreadTyping: true });

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

    // channel that is expected to be rendered
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        hasTimeControl: true,
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, { hasThreadTyping: true });

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

    // channel that is expected to be rendered
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        hasTimeControl: true,
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, { hasThreadTyping: true });

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

    // channel that is expected to be rendered
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        hasTimeControl: true,
        async mockRPC(route, args) {
            if (args.method === 'notify_typing') {
                assert.step(`notify_typing:${args.kwargs.is_typing}`);
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, { hasThreadTyping: true });

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

QUnit.test('composer: send button is disabled if attachment upload is not finished', async function (assert) {
    assert.expect(8);

    const attachmentUploadedPromise = makeTestPromise();
    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start({
        async mockFetch(resource, init) {
            const res = this._super(...arguments);
            if (resource === '/mail/attachment/upload') {
                await attachmentUploadedPromise;
            }
            return res;
        }
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard',
        "should have an attachment after a file has been input"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard.o-isUploading',
        "attachment displayed is being uploaded"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer_buttonSend',
        "composer send button should be displayed"
    );
    assert.ok(
        !!document.querySelector('.o_Composer_buttonSend').attributes.disabled,
        "composer send button should be disabled as attachment is not yet uploaded"
    );

    // simulates attachment finishes uploading
    await afterNextRender(() => attachmentUploadedPromise.resolve());
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard',
        "should have only one attachment"
    );
    assert.containsNone(
        document.body,
        '.o_AttachmentCard.o-isUploading',
        "attachment displayed should be uploaded"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer_buttonSend',
        "composer send button should still be present"
    );
    assert.ok(
        !document.querySelector('.o_Composer_buttonSend').attributes.disabled,
        "composer send button should be enabled as attachment is now uploaded"
    );
});

QUnit.test('warning on send with shortcut when attempting to post message with still-uploading attachments', async function (assert) {
    assert.expect(7);

    const { createComposerComponent } = await this.start({
        async mockFetch(resource, init) {
            const res = this._super(...arguments);
            if (resource === '/mail/attachment/upload') {
                // simulates attachment is never finished uploading
                await new Promise(() => {});
            }
            return res;
        },
        services: {
            notification: {
                notify(params) {
                    assert.strictEqual(
                        params.message,
                        "Please wait while the file is uploading.",
                        "notification content should be about the uploading file"
                    );
                    assert.strictEqual(
                        params.type,
                        'warning',
                        "notification should be a warning"
                    );
                    assert.step('notification');
                }
            }
        },
    });
    const thread = this.messaging.models['mail.thread'].create({
        composer: insertAndReplace({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await createComposerComponent(thread.composer, {
        textInputSendShortcuts: ['enter'],
    });
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
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard',
        "should have only one attachment"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard.o-isUploading',
        "attachment displayed is being uploaded"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer_buttonSend',
        "composer send button should be displayed"
    );

    // Try to send message
    document
        .querySelector(`.o_ComposerTextInput_textarea`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    assert.verifySteps(
        ['notification'],
        "should have triggered a notification for inability to post message at the moment (some attachments are still being uploaded)"
    );
});

QUnit.test('remove an attachment from composer does not need any confirmation', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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
    assert.containsOnce(
        document.body,
        '.o_Composer_attachmentList',
        "should have an attachment list"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer .o_AttachmentCard',
        "should have only one attachment"
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentCard_asideItemUnlink').click()
    );
    assert.containsNone(
        document.body,
        '.o_Composer .o_AttachmentCard',
        "should not have any attachment left after unlinking the only one"
    );
});

QUnit.test('remove an uploading attachment', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start({
        async mockFetch(resource, init) {
            const res = this._super(...arguments);
            if (resource === '/mail/attachment/upload') {
                // simulates uploading indefinitely
                await new Promise(() => {});
            }
            return res;
        }
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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
    assert.containsOnce(
        document.body,
        '.o_Composer_attachmentList',
        "should have an attachment list"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer .o_AttachmentCard',
        "should have only one attachment"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard.o-isUploading',
        "should have an uploading attachment"
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentCard_asideItemUnlink').click());
    assert.containsNone(
        document.body,
        '.o_Composer .o_AttachmentCard',
        "should not have any attachment left after unlinking uploading one"
    );
});

QUnit.test('remove an uploading attachment aborts upload', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start({
        async mockFetch(resource, init) {
            const res = this._super(...arguments);
            if (resource === '/mail/attachment/upload') {
                // simulates uploading indefinitely
                await new Promise(() => {});
            }
            return res;
        }
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
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
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard',
        "should contain an attachment"
    );
    const attachmentLocalId = document.querySelector('.o_AttachmentCard').dataset.id;

    await this.afterEvent({
        eventName: 'o-attachment-upload-abort',
        func: () => {
            document.querySelector('.o_AttachmentCard_asideItemUnlink').click();
        },
        message: "attachment upload request should have been aborted",
        predicate: ({ attachment }) => {
            return attachment.localId === attachmentLocalId;
        },
    });
});

QUnit.test("Show a default status in the recipient status text when the thread doesn't have a name.", async function (assert) {
    assert.expect(1);

    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        composer: insertAndReplace({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await createComposerComponent(thread.composer, { hasFollowers: true });
    assert.strictEqual(
        document.querySelector('.o_Composer_followers').textContent.replace(/\s+/g, ''),
        "To:Followersofthisdocument",
        "Composer should display \"To: Followers of this document\" if the thread as no name."
    );
});

QUnit.test("Show a thread name in the recipient status text.", async function (assert) {
    assert.expect(1);

    const { createComposerComponent } = await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        name: "test name",
        composer: insertAndReplace({ isLog: false }),
        id: 20,
        model: 'res.partner',
    });
    await createComposerComponent(thread.composer, { hasFollowers: true });
    assert.strictEqual(
        document.querySelector('.o_Composer_followers').textContent.replace(/\s+/g, ''),
        "To:Followersof\"testname\"",
        "basic rendering when sending a message to the followers and thread does have a name"
    );
});

QUnit.test('send message only once when button send is clicked twice quickly', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    // Type message
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "test message");
    });

    await afterNextRender(() => {
        document.querySelector(`.o_Composer_buttonSend`).click();
        document.querySelector(`.o_Composer_buttonSend`).click();
    });
    assert.verifySteps(
        ['message_post'],
        "The message has been posted only once"
    );
});

QUnit.test('send message only once when enter is pressed twice quickly', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    const { createComposerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer, {
        textInputSendShortcuts: ['enter'],
    });
    // Type message
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "test message");
    });
    await afterNextRender(() => {
        const enterEvent = new window.KeyboardEvent('keydown', { key: 'Enter' });
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(enterEvent);
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(enterEvent);
    });
    assert.verifySteps(
        ['message_post'],
        "The message has been posted only once"
    );
});

QUnit.test('[technical] does not crash when an attachment is removed before its upload starts', async function (assert) {
    // Uploading multiple files uploads attachments one at a time, this test
    // ensures that there is no crash when an attachment is destroyed before its
    // upload started.
    assert.expect(1);

    // Promise to block attachment uploading
    const uploadPromise = makeTestPromise();
    this.data['mail.channel'].records.push({
        id: 20,
    });
    const { createComposerComponent } = await this.start({
        async mockFetch(resource) {
            const _super = this._super.bind(this, ...arguments);
            if (resource === '/mail/attachment/upload') {
                await uploadPromise;
            }
            return _super();
        },
    });
    const thread = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await createComposerComponent(thread.composer);
    const file1 = await createFile({
        name: 'text1.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    const file2 = await createFile({
        name: 'text2.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });
    await afterNextRender(() =>
        inputFiles(
            document.querySelector('.o_FileUploader_input'),
            [file1, file2]
        )
    );
    await afterNextRender(() => {
            Array.from(document.querySelectorAll('div'))
            .find(el => el.textContent === 'text2.txt')
            .closest('.o_AttachmentCard')
            .querySelector('.o_AttachmentCard_asideItemUnlink')
            .click();
        }
    );
    // Simulates the completion of the upload of the first attachment
    uploadPromise.resolve();
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard:contains("text1.txt")',
        "should only have the first attachment after cancelling the second attachment"
    );
});

});
});
});
