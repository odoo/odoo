odoo.define('mail.component.ComposerTests', function (require) {
'use strict';

const Composer = require('mail.component.Composer');
const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    dragoverFiles,
    dropFiles,
    inputFiles,
    pasteFiles,
    pause,
    start: utilsStart,
} = require('mail.owl.testUtils');

const testUtils = require('web.test_utils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Composer', {
    beforeEach() {
        utilsBeforeEach(this);

        /**
         * @param {integer} composerId
         * @param {Object} [otherProps]
         */
        this.createComposer = async (composerId, otherProps) => {
            const env = await this.widget.call('env', 'get');
            this.composer = new Composer(env, {
                id: composerId,
                ...otherProps,
            });
            await this.composer.mount(this.widget.$el[0]);
            await testUtils.nextTick();
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { store, widget } = await utilsStart({
                ...params,
                data: this.data,
            });
            this.store = store;
            this.widget = widget;
        };
    },
    async afterEach() {
        utilsAfterEach(this);
        if (this.composer) {
            this.composer.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.store = undefined;
        await testUtils.nextTick(); // tribute detach is asynchronous
    }
});

QUnit.test('composer text input: basic rendering', async function (assert) {
    assert.expect(9);

    await this.start();
    await this.createComposer('composer_1');
    assert.strictEqual(
        document
            .querySelectorAll('.o_Composer')
            .length,
        1,
        "should have composer in discuss thread");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Composer_textInput')
            .length,
        1,
        "should have text input inside discuss thread composer");
    assert.ok(
        document
            .querySelector('.o_Composer_textInput')
            .classList
            .contains('o_ComposerTextInput'),
        "composer text input of composer should be a ComposerTextIput component");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_ComposerTextInput
                > .note-editor`)
            .length,
        1,
        "should have note editor inside composer text input");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_ComposerTextInput
                > .note-editor
                > .note-editing-area`)
            .length,
        1,
        "should have note editing area inside note editor of composer text input");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_ComposerTextInput
                > .note-editor
                > .note-editing-area
                > .note-editable`)
            .length,
        1,
        "should have note editable inside note editing areea of composer text input");
    assert.ok(
        document
            .querySelector(`
                .o_ComposerTextInput
                > .note-editor
                > .note-editing-area
                > .note-editable`)
            .classList
            .contains('o_ComposerTextInput_editable'),
        "should have easy access to editable of composer text input");
    assert.ok(
        document
            .querySelector(`
                .o_ComposerTextInput_editable`)
            .isContentEditable,
        "should have note editable as an HTML editor");
    assert.strictEqual(
        document
            .querySelector(`
                .o_ComposerTextInput_editable`)
            .dataset
            .placeholder,
        "Write something...",
        "should have placeholder in note editable of composer text input");
});

QUnit.test('add an emoji', async function (assert) {
    assert.expect(1);

    await this.start();
    await this.createComposer('composer_1');
    document
        .querySelector('.o_Composer_buttonEmojis')
        .click();
    await testUtils.nextTick(); // re-render
    document
        .querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]')
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "😊",
        "emoji should be inserted in the composer text input");
});

QUnit.test('add an emoji after some text', async function (assert) {
    assert.expect(2);

    await this.start();
    await this.createComposer('composer_1');
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "Blabla");
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "Blabla",
        "composer text input should have text only initially");

    document
        .querySelector('.o_Composer_buttonEmojis')
        .click();
    await testUtils.nextTick(); // re-render
    document
        .querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]')
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "Blabla😊",
        "emoji should be inserted after the text");
});

QUnit.test('add emoji replaces (keyboard) text selection', async function (assert) {
    assert.expect(2);

    await this.start();
    await this.createComposer('composer_1');
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "Blabla");
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "Blabla",
        "composer text input should have text only initially");

    // simulate selection of all the content by keyboard
    const range = document.createRange();
    range.selectNodeContents(
        document
            .querySelector(`.o_ComposerTextInput_editable`));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document
            .querySelector(`.o_ComposerTextInput_editable`)
            .dispatchEvent(
                new window.KeyboardEvent('keydown', {
                    key: 'ArrowLeft',
                }));
    // select emoji
    document
        .querySelector('.o_Composer_buttonEmojis')
        .click();
    await testUtils.nextTick(); // re-render
    document
        .querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]')
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent
            .replace(/\s/, " "),
        "😊 ", // AKU: for some reasons, it adds &nbsp; after emoji
        "whole text selection should have been replaced by emoji");
});

QUnit.test('add emoji replaces (mouse) text selection', async function (assert) {
    assert.expect(2);

    await this.start();
    await this.createComposer('composer_1');
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "Blabla");
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "Blabla",
        "composer text input should have text only initially");

    // simulate selection of all the content by keyboard
    const range = document.createRange();
    range.selectNodeContents(
        document
            .querySelector(`.o_ComposerTextInput_editable`));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document
            .querySelector(`.o_ComposerTextInput_editable`)
            .dispatchEvent(new window.MouseEvent('mouseup'));
    // select emoji
    document
        .querySelector('.o_Composer_buttonEmojis')
        .click();
    await testUtils.nextTick(); // re-render
    document
        .querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]')
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent
            .replace(/\s/, " "),
        "😊 ", // AKU: for some reasons, it adds &nbsp; after emoji
        "whole text selection should have been replaced by emoji");
});

QUnit.test('display partner mention suggestions on typing "@"', async function (assert) {
    assert.expect(2);

    await this.start();
    await this.createComposer('composer_1');
    assert.strictEqual(
        document
            .querySelectorAll(`.tribute-container`)
            .length,
        0,
        "should not display the tribute mention suggestions initially");

    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "@");
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`.tribute-container`)
            .length,
        1,
        "should display the tribute mention suggestions on typing '@'");
});

QUnit.test('mention a partner', async function (assert) {
    assert.expect(4);

    await this.start();
    await this.createComposer('composer_1');
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "",
        "text content of composer should be empty initially");

    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "@");
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await testUtils.nextTick(); // re-render
    document
        .querySelectorAll('.o_ComposerTextInput_mentionMenuItem')[0]
        .dispatchEvent(new window.MouseEvent('mousedown', { bubbles: true }));
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent
            .replace(/\s/, " "),
        "@OdooBot ",
        "text content of composer should have mentionned partner + additional whitespace afterwards");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_ComposerTextInput_editable
                a.o_mention`)
            .length,
        1,
        "there should be a mention link in the composer");
    assert.strictEqual(
        document
            .querySelector(`
                .o_ComposerTextInput_editable
                a.o_mention`)
            .textContent,
        "@OdooBot",
        "mention link should have textual '@mention' as text content");
});

QUnit.test('mention a partner after some text', async function (assert) {
    assert.expect(4);

    await this.start();
    await this.createComposer('composer_1');

    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "bluhbluh");
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "bluhbluh",
        "text content of composer should be empty initially");
    document.execCommand('insertText', false, "@");
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await testUtils.nextTick(); // re-render
    document
        .querySelectorAll('.o_ComposerTextInput_mentionMenuItem')[0]
        .dispatchEvent(new window.MouseEvent('mousedown', { bubbles: true }));
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent
            .replace(/\s/, " "),
        "bluhbluh@OdooBot ",
        "text content of composer should have previous content + mentionned partner + additional whitespace afterwards");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_ComposerTextInput_editable
                a.o_mention`)
            .length,
        1,
        "there should be a mention link in the composer");
    assert.strictEqual(
        document
            .querySelector(`
                .o_ComposerTextInput_editable
                a.o_mention`)
            .textContent,
        "@OdooBot",
        "mention link should have textual '@mention' as text content");
});

QUnit.test('add an emoji after a partner mention', async function (assert) {
    assert.expect(4);

    await this.start();
    await this.createComposer('composer_1');

    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "@");
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await testUtils.nextTick(); // re-render
    document
        .querySelectorAll('.o_ComposerTextInput_mentionMenuItem')[0]
        .dispatchEvent(new window.MouseEvent('mousedown', { bubbles: true }));
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent
            .replace(/\s/, " "),
        "@OdooBot ",
        "text content of composer should have previous content + mentionned partner + additional whitespace afterwards");

    // select emoji
    document
        .querySelector('.o_Composer_buttonEmojis')
        .click();
    await testUtils.nextTick(); // re-render
    document
        .querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]')
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent
            .replace(/\s/, " "),
        "@OdooBot 😊",
        "text content of composer should have previous mention and selected emoji just after");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_ComposerTextInput_editable
                a.o_mention`)
            .length,
        1,
        "there should still be a mention link in the composer");
    assert.strictEqual(
        document
            .querySelector(`
                .o_ComposerTextInput_editable
                a.o_mention`)
            .textContent,
        "@OdooBot",
        "mention link should still have textual '@mention' as text content (no emoji)");
});

QUnit.test('composer: add an attachment', async function (assert) {
    assert.expect(9);

    await this.start();
    await this.createComposer('composer_1', {
        attachmentsLayout: 'card',
    });

    const file = await testUtils.file.createFile({
        content: 'hello, world',
        contentType: 'text/plain',
        name: 'text.txt',
    });
    await inputFiles(
        document.querySelector('.o_Composer_fileInput'),
        [file]);
    assert.ok(
        document.querySelector('.o_Composer_attachmentList'),
        "should have an attachment list");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment`),
        "should have an attachment");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment_image`),
        "should have an attachment image");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment_main`),
        "should have an attachment main part");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment_filename`),
        "should have an attachment filename");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment_extension`),
        "should have an attachment extension");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment_aside`),
        "should have an attachment aside");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment_asideItemUploaded`),
        "should have an attachment uploaded icon");
    assert.ok(
        document
            .querySelector(`
                .o_Composer_attachmentList
                .o_Attachment_asideItemUnlink`),
        "should have an attachment remove button");
});

QUnit.test('composer: drop attachments', async function (assert) {
    assert.expect(3);

    await this.start();
    await this.createComposer('composer_1');
    const files = [
        await testUtils.file.createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        }),
        await testUtils.file.createFile({
            content: 'hello, worlduh',
            contentType: 'text/plain',
            name: 'text2.txt',
        }),
    ];
    await dragoverFiles(document.querySelector('.o_Composer'));
    assert.ok(
        document.querySelector('.o_Composer_dropZone'),
        "should have a drop zone");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)
            .length,
        0,
        "should have no attachment before files are dropped");

    await dropFiles(
        document.querySelector('.o_Composer_dropZone'),
        files);
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)
            .length,
        2,
        "should have 2 attachments in the composer after files dropped");
});

QUnit.test('composer: paste attachments', async function (assert) {
    assert.expect(2);

    await this.start();
    await this.createComposer('composer_1');

    const files = [
        await testUtils.file.createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        }),
        await testUtils.file.createFile({
            content: 'hello, worlduh',
            contentType: 'text/plain',
            name: 'text2.txt',
        }),
    ];
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)
            .length,
        0,
        "should not have any attachment in the composer before paste");

    await pasteFiles(document.querySelector('.o_ComposerTextInput'), files);
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)
            .length,
        2,
        "should have 2 attachments in the composer after paste");
});

});
});
});
