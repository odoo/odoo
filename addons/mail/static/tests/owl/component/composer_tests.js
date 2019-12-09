odoo.define('mail.component.ComposerTests', function (require) {
'use strict';

const Composer = require('mail.component.Composer');
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    dragenterFiles,
    dropFiles,
    inputFiles,
    nextAnimationFrame,
    pasteFiles,
    pause,
    start: utilsStart,
} = require('mail.owl.testUtils');

const { file: { createFile } } = require('web.test_utils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Composer', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createComposerComponent = async (composerLocalId, otherProps) => {
            Composer.env = this.env;
            this.composer = new Composer(null, Object.assign({
                composerLocalId,
            }, otherProps));
            await this.composer.mount(this.widget.$el[0]);
            await afterNextRender();
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
        if (this.composer) {
            this.composer.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete Composer.env;
        await nextAnimationFrame(); // ensures tribute is detached on next frame
    }
});

QUnit.test('composer text input: basic rendering', async function (assert) {
    assert.expect(6);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
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
        document.querySelectorAll(`.o_ComposerTextInput_editable`).length,
        1,
        "should have editable part inside composer text input"
    );
    assert.ok(
        document.querySelector(`.o_ComposerTextInput_editable`).isContentEditable,
        "should have note editable as an HTML editor"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).dataset.placeholder,
        "Write something...",
        "should have placeholder in note editable of composer text input"
    );
});

QUnit.test('add an emoji', async function (assert) {
    assert.expect(1);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    document.querySelector('.o_Composer_buttonEmojis').click();
    await afterNextRender();
    document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent,
        "😊",
        "emoji should be inserted in the composer text input"
    );
});

QUnit.test('add an emoji after some text', async function (assert) {
    assert.expect(2);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    document.querySelector(`.o_ComposerTextInput_editable`).focus();
    document.execCommand('insertText', false, "Blabla");
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent,
        "Blabla",
        "composer text input should have text only initially"
    );

    document.querySelector('.o_Composer_buttonEmojis').click();
    await afterNextRender();
    document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent,
        "Blabla😊",
        "emoji should be inserted after the text"
    );
});

QUnit.test('add emoji replaces (keyboard) text selection', async function (assert) {
    assert.expect(2);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    document.querySelector(`.o_ComposerTextInput_editable`).focus();
    document.execCommand('insertText', false, "Blabla");
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent,
        "Blabla",
        "composer text input should have text only initially"
    );

    // simulate selection of all the content by keyboard
    const range = document.createRange();
    range.selectNodeContents(
        document.querySelector(`.o_ComposerTextInput_editable`)
    );
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.querySelector(`.o_ComposerTextInput_editable`).dispatchEvent(
        new window.KeyboardEvent('keydown', {
            key: 'ArrowLeft',
        })
    );
    // select emoji
    document.querySelector('.o_Composer_buttonEmojis').click();
    await afterNextRender();
    document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent.replace(/\s/, " "),
        "😊 ", // AKU: for some reasons, it adds &nbsp; after emoji
        "whole text selection should have been replaced by emoji"
    );
});

QUnit.test('add emoji replaces (mouse) text selection', async function (assert) {
    assert.expect(2);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    document.querySelector(`.o_ComposerTextInput_editable`).focus();
    document.execCommand('insertText', false, "Blabla");
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent,
        "Blabla",
        "composer text input should have text only initially"
    );

    // simulate selection of all the content by keyboard
    const range = document.createRange();
    range.selectNodeContents(
        document.querySelector(`.o_ComposerTextInput_editable`)
    );
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.MouseEvent('mouseup'));
    // wait event handled
    await nextAnimationFrame();
    // select emoji
    document.querySelector('.o_Composer_buttonEmojis').click();
    await afterNextRender();
    document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent.replace(/\s/, " "),
        "😊 ", // AKU: for some reasons, it adds &nbsp; after emoji
        "whole text selection should have been replaced by emoji"
    );
});

QUnit.test('display partner mention suggestions on typing "@"', async function (assert) {
    assert.expect(2);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.tribute-container`).length,
        0,
        "should not display the tribute mention suggestions initially"
    );

    document.querySelector(`.o_ComposerTextInput_editable`).focus();
    document.execCommand('insertText', false, "@");
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.tribute-container`).length,
        1,
        "should display the tribute mention suggestions on typing '@'"
    );
});

QUnit.test('mention a partner', async function (assert) {
    assert.expect(4);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent,
        "",
        "text content of composer should be empty initially"
    );

    document.querySelector(`.o_ComposerTextInput_editable`).focus();
    document.execCommand('insertText', false, "@");
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await afterNextRender();
    document.querySelectorAll('.o_ComposerTextInput_mentionMenuItem')[0]
        .dispatchEvent(new window.MouseEvent('mousedown', { bubbles: true }));
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent.replace(/\s/, " "),
        "@OdooBot ",
        "text content of composer should have mentionned partner + additional whitespace afterwards"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ComposerTextInput_editable a.o_mention`).length,
        1,
        "there should be a mention link in the composer"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable a.o_mention`).textContent,
        "@OdooBot",
        "mention link should have textual '@mention' as text content"
    );
});

QUnit.test('mention a partner after some text', async function (assert) {
    assert.expect(4);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    document.querySelector(`.o_ComposerTextInput_editable`).focus();
    document.execCommand('insertText', false, "bluhbluh");
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent,
        "bluhbluh",
        "text content of composer should be empty initially"
    );
    document.execCommand('insertText', false, "@");
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await afterNextRender();
    document.querySelectorAll('.o_ComposerTextInput_mentionMenuItem')[0]
        .dispatchEvent(new window.MouseEvent('mousedown', { bubbles: true }));
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent.replace(/\s/, " "),
        "bluhbluh@OdooBot ",
        "text content of composer should have previous content + mentionned partner + additional whitespace afterwards"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ComposerTextInput_editable a.o_mention`).length,
        1,
        "there should be a mention link in the composer"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable a.o_mention`).textContent,
        "@OdooBot",
        "mention link should have textual '@mention' as text content"
    );
});

QUnit.test('add an emoji after a partner mention', async function (assert) {
    assert.expect(4);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
    document.querySelector(`.o_ComposerTextInput_editable`).focus();
    document.execCommand('insertText', false, "@");
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    await afterNextRender();
    document.querySelectorAll('.o_ComposerTextInput_mentionMenuItem')[0]
        .dispatchEvent(new window.MouseEvent('mousedown', { bubbles: true }));
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent.replace(/\s/, " "),
        "@OdooBot ",
        "text content of composer should have previous content + mentionned partner + additional whitespace afterwards"
    );

    // select emoji
    document.querySelector('.o_Composer_buttonEmojis').click();
    await afterNextRender();
    document.querySelector('.o_EmojisPopover_emoji[data-unicode="😊"]').click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable`).textContent.replace(/\s/, " "),
        "@OdooBot 😊",
        "text content of composer should have previous mention and selected emoji just after"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ComposerTextInput_editable a.o_mention`).length,
        1,
        "there should still be a mention link in the composer"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_editable a.o_mention`).textContent,
        "@OdooBot",
        "mention link should still have textual '@mention' as text content (no emoji)"
    );
});

QUnit.test('composer: add an attachment', async function (assert) {
    assert.expect(2);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId, { attachmentsDetailsMode: 'card' });
    const file = await createFile({
        content: 'hello, world',
        contentType: 'text/plain',
        name: 'text.txt',
    });
    inputFiles(
        document.querySelector('.o_FileUploader_input'),
        [file]
    );
    await afterNextRender();
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
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
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
    dragenterFiles(document.querySelector('.o_Composer'));
    await afterNextRender();
    assert.ok(
        document.querySelector('.o_Composer_dropZone'),
        "should have a drop zone"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        0,
        "should have no attachment before files are dropped"
    );

    dropFiles(
        document.querySelector('.o_Composer_dropZone'),
        files
    );
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        2,
        "should have 2 attachments in the composer after files dropped"
    );

    dragenterFiles(document.querySelector('.o_Composer'));
    await afterNextRender();
    dropFiles(
        document.querySelector('.o_Composer_dropZone'),
        [
            await createFile({
                content: 'hello, world',
                contentType: 'text/plain',
                name: 'text3.txt',
            })
        ]
    );
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        3,
        "should have 3 attachments in the box after files dropped"
    );
});

QUnit.test('composer: paste attachments', async function (assert) {
    assert.expect(2);

    await this.start();
    const composerLocalId = this.env.store.dispatch('_createComposer');
    await this.createComposerComponent(composerLocalId);
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

    pasteFiles(document.querySelector('.o_ComposerTextInput'), files);
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        1,
        "should have 1 attachment in the composer after paste"
    );
});

});
});
});
