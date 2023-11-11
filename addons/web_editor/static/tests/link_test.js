/** @odoo-module **/
import { getDeepRange, setSelection } from '@web_editor/js/editor/odoo-editor/src/utils/utils';
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { patchWithCleanup, nextTick, triggerHotkey } from '@web/../tests/helpers/utils';
import { Wysiwyg } from '@web_editor/js/wysiwyg/wysiwyg';
import {
    triggerEvent,
    insertText,
    insertParagraphBreak,
} from '@web_editor/js/editor/odoo-editor/test/utils';

function onMount() {
    const editor = wysiwyg.odooEditor;
    const editable = editor.editable;
    editor.testMode = true;
    return { editor, editable };
}

async function inputText(selector, content, { replace = false } = {}) {
    if (replace) {
        document.querySelector(selector).value = "";
    }
    document.querySelector(selector).focus();
    for (const char of content) {
        document.execCommand("insertText", false, char);
        document
            .querySelector(selector)
            .dispatchEvent(new window.KeyboardEvent("keydown", { key: char }));
        document
            .querySelector(selector)
            .dispatchEvent(new window.KeyboardEvent("keyup", { key: char }));
    }
}

let serverData;
let wysiwyg;

QUnit.module('web_editor', {
    before: function () {
        serverData = {
            models: {
                note: {
                    fields: {
                        body: {
                            string: "Editor",
                            type: "html"
                        },
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
                        body: '<p><br></p>',
                    }],
                },
            },
        };
    },
    beforeEach: function () {
        setupViewRegistries();
        patchWithCleanup(Wysiwyg.prototype, {
            init() {
                super.init(...arguments);
                wysiwyg = this;
            }
        });
    }
}, function () {

    QUnit.module('HotKeys');

    QUnit.test('should be able to create link with ctrl+k', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        await nextTick();
        triggerEvent(node, "keydown", {
            key: "K",
            ctrlKey: true,
        });
        await nextTick();
        await inputText('.o_command_palette_search', "k");
        await nextTick();
        triggerEvent(node, "keydown", {
            key: "Enter"
        })
        await nextTick();
        inputText('input[id="o_link_dialog_url_input"]', '#')
        await nextTick();
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        assert.strictEqual(editable.innerHTML, '<p><a href="#" target="_blank" class="" contenteditable="true">#</a><br></p>');
    });

    QUnit.test('should be able to create link with ctrl+k ctrl+k', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        await nextTick();
        triggerEvent(node, "keydown", {
            key: "K",
            ctrlKey: true,
        });
        await nextTick();
        const input = editor.document.querySelector('input.form-control');
        await nextTick();
        triggerEvent(input, "keydown", {
            key: "K",
            ctrlKey: true,
        });
        await nextTick();
        inputText('input[id="o_link_dialog_url_input"]', '#')
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        assert.strictEqual(editable.innerHTML, '<p><a href="#" target="_blank" class="" contenteditable="true">#</a><br></p>');
    });

    QUnit.test('should be able to create link with ctrl+k , and should make link on two existing characters', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        insertText(editor, "Hello");
        getDeepRange(node, { splitText: true, select: true });
        setSelection(node, 1, node, 3);
        await nextTick();
        triggerEvent(node, "keydown", {
            key: "K",
            ctrlKey: true,
        });
        await nextTick();
        await inputText('.o_command_palette_search', "k");
        await nextTick();
        triggerEvent(node, "keydown", {
            key: "Enter"
        })
        await nextTick();
        inputText('input[id="o_link_dialog_url_input"]', '#')
        await nextTick();
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p>H<a href="#" target="_blank" class="" contenteditable="true">el</a>lo</p>');
        await nextTick();
    });

    /*-------------------------------------------------------------------------------------------------------------------------------------------------------------------*/

    QUnit.module('Typing based');

    QUnit.test('typing www.odoo.com + space should convert to link', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', "www.odoo.com");
        insertText(editor, ' ');
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p><a href="http://www.odoo.com">www.odoo.com</a> </p>');
    });

    QUnit.test('typing odoo.com + space should convert to link', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', "odoo.com");
        await nextTick();
        insertText(editor, ' ');
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p><a href="http://odoo.com">odoo.com</a> </p>');
    });

    QUnit.test('typing http://odoo.com + space should convert to link', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', "http://odoo.com");
        insertText(editor, ' ');
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p><a href="http://odoo.com">http://odoo.com</a> </p>');
    });

    QUnit.test('typing http://google.co.in + space should convert to link', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', "http://google.co.in");
        insertText(editor, ' ');
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p><a href="http://google.co.in">http://google.co.in</a> </p>');
    });

    QUnit.test('typing www.odoo + space should not convert to link', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', "www.odoo");
        insertText(editor, ' ');
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p>www.odoo </p>');
    });

    /*--------------------------------------------------------------------------------------------------------------------------------------------------------------*/

    QUnit.module('Toolbar based');

    QUnit.test('should convert all selected text to link', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        insertText(editor, "Hello");
        getDeepRange(node, { splitText: true, select: true });
        triggerEvent(node, "keydown", { key :"a", ctrlKey: true });
        await nextTick();
        editor.document.querySelector('.fa-link ').click();
        await nextTick();
        inputText('input[id="o_link_dialog_url_input"]', '#')
        await nextTick();
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p><a href="#" target="_blank" class="" contenteditable="true">Hello</a></p>');
        await nextTick();
    });

    QUnit.test('should set the link on two existing characters', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        insertText(editor, "Hello");
        getDeepRange(node, { splitText: true, select: true });
        setSelection(node, 1, node, 3);
        await nextTick();
        editor.document.querySelector('.fa-link ').click();
        await nextTick();
        inputText('input[id="o_link_dialog_url_input"]', '#')
        await nextTick();
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p>H<a href="#" target="_blank" class="" contenteditable="true">el</a>lo</p>');
        await nextTick();
    });

    QUnit.test('should change the existing label by new character', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        insertText(editor, "abccde")
        getDeepRange(node, { splitText: true, select: true });
        setSelection(node, 1, node, 3);
        await nextTick();
        editor.document.querySelector('.fa-link ').click();
        await nextTick();
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        inputText('.odoo-editor-editable p', `B`);
        assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true" data-oe-zws-empty-inline="">B\u200B</a>cde</p>`)
        await nextTick();
    });

    //Todo : this test case will work after jili's fix (task-3181486)
    QUnit.test('Should be able to insert link on empty p', async function (assert) {
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        triggerEvent(node, "keydown", { key :"a", ctrlKey: true });
        await nextTick();
        editor.document.querySelector('.fa-link ').click();
        await nextTick();
        inputText('input[id="o_link_dialog_url_input"]', '#')
        await nextTick();
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        assert.strictEqual(editable.innerHTML, '<p><a href="#" target="_blank" class="" contenteditable="true"><br></a></p>');
        await nextTick();
    });

    /*------------------------------------------------------------------------------------------------------------------------------------------------------------------------------*/

    QUnit.module('PowerBox related');

    // Todo: will work when ages's task will be merged. (task-3234749)
    QUnit.test('should insert a link and preserve spacing', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', 'a     b');
        const selection = setSelection(node.firstChild, 3 , node.firstChild, 3);
        await insertText(editor, "/");
        await insertText(editor, "link");
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
        await nextTick();
        debugger
        // editor.document.querySelector('.oe-powerbox-commandWrapper').click();
        triggerEvent(node, "keydown", { key: "Enter" });
        await nextTick();
        node.focus();
        await inputText('input[id="o_link_dialog_label_input"]', 'link');
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        // setSelection(node, 0);
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">link</a><br></p>`);
        // Todo to change it to this once this task is merged (task-3446357)
        // assert.strictEqual(editable.innerHTML, `<p>a\u200B \u200B;<a href="#" target="_blank" class="">link</a> \u200Bb</p>`);
        await nextTick();
    });

    QUnit.test('should insert a link and write a character after the link is created', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
            '<field name="body" widget="html" style="height: 100px"/>' +
            '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', `ab`);
        setSelection(node.firstChild, 1);
        await insertText(editor, "/");
        await insertText(editor, "link");
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
        await nextTick();
        triggerEvent(editor.editable, "keydown", { key: "Enter" });
        await nextTick();
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        editor.document.getSelection().collapseToEnd();
        await insertText(editor, "D");
        await nextTick();
        // Todo: to change this assert when this task will be merged. (task-3446357)
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">#D</a><br></p>`)
        // Todo: change it to this
        // assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true">#D</a>b</p>`)
        await nextTick();
    });

    QUnit.test('should insert a link and write 2 character after the link is created', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', `ab`);
        setSelection(node.firstChild, 1);
        await insertText(editor, "/");
        await insertText(editor, "link");
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
         await nextTick();
        triggerEvent(editor.editable, "keydown", { key: "Enter" });
        await nextTick();
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        editor.document.getSelection().collapseToEnd();
        await insertText(editor, "E");
        await insertText(editor, "D");
        await nextTick();
        
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">#ED</a><br></p>`);
        // Todo: to change this assert to this when this task will be merged. (task-3446357)
        // assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true">#ED</a>b</p>`);
        await nextTick();
    });

    QUnit.test('should insert a link and write a character after the link then create a new <p>', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', `ab`);
        setSelection(node.firstChild, 1);
        await insertText(editor, "/");
        await insertText(editor, "link");
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
         await nextTick();
            triggerEvent(editor.editable, "keydown", { key: "Enter" });
        await nextTick();
        await inputText('input[id="o_link_dialog_label_input"]', 'link');
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        editor.document.getSelection().collapseToEnd();
        await insertText(editor, "E");
        await insertParagraphBreak(editor);
        await nextTick();
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">linkE</a></p><p><br></p>`);
        // Todo: to change this assert to this when this task will be merged. (task-3446357)
        // assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true">link</a>E</p><p>b</p>`)
        await nextTick();
    });

    QUnit.test('should insert a link and write a character, a new <p> and another character', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', `ab`);
        // getDeepRange(node, { splitText: true, select: true });
        setSelection(node.firstChild, 1);
        await insertText(editor, "/");
        await insertText(editor, "link");
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
         await nextTick();
        triggerEvent(editor.editable, "keydown", { key: "Enter" });
        await nextTick();
        await inputText('input[id="o_link_dialog_label_input"]', 'link');
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        editor.document.getSelection().collapseToEnd();
        await insertText(editor, "E");
        await insertParagraphBreak(editor);
        await insertText(editor, "D");
        await nextTick();
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">linkE</a></p>D<p><br></p>`);
        // Todo: to change this assert to this when this task will be merged. (task-3446357)
        // assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true">link</a>E</p><p>Db</p>`)
        await nextTick();
    });
    
    QUnit.test('should insert a link and write a character at the end of the link then insert a <br>', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', `ab`);
        // getDeepRange(node, { splitText: true, select: true });
        setSelection(node.firstChild, 1);
        await insertText(editor, "/");
        await insertText(editor, "link");
         await nextTick();
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
        triggerEvent(editor.editable, "keydown", { key: "Enter" });
        await nextTick();
        await inputText('input[id="o_link_dialog_label_input"]', 'link');
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        editor.document.getSelection().collapseToEnd();
        await insertText(editor, "E");
        triggerEvent(node, "keydown", { key: "Enter", shiftKey: true });
        await nextTick();
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">linkE<br></a><br></p>`);
        // Todo: to change this assert to this when this task will be merged. (task-3446357)
        // assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true">link</a>E<br>b</p>`)
        await nextTick();
    });

    QUnit.test('should insert a link and write a character insert a <br> and another character', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', `ab`);
        // getDeepRange(node, { splitText: true, select: true });
        setSelection(node.firstChild, 1);
        await insertText(editor, "/");
        await insertText(editor, "link");
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
        await nextTick();
        triggerEvent(editor.editable, "keydown", { key: "Enter" });
        await nextTick();
        await inputText('input[id="o_link_dialog_label_input"]', 'link');
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        editor.document.getSelection().collapseToEnd();
        await nextTick();
        await insertText(editor, "E");
        triggerEvent(node, "keydown", { key: "Enter", shiftKey: true });
        await insertText(editor, "D");
        await nextTick();
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">linkE<br>D</a></p>`);
        // Todo: to change this assert to this when this task will be merged. (task-3446357)
        // assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true">link</a>E<br>Db</p>`);
        await nextTick();
    });

    QUnit.test('should insert a link and write a character insert a <br> and another character', async function (assert) {
        assert.strictEqual(4,4);
        await makeView({
            type: 'form',
            serverData,
            resModel: 'note',
            arch: '<form>' +
                '<field name="body" widget="html" style="height: 100px"/>' +
                '</form>',
            resId: 1,
        });
        const { editor, editable } = onMount();
        const node = editable.querySelector('p');
        setSelection(node, 0);
        inputText('.odoo-editor-editable p', `ab`);
        // getDeepRange(node, { splitText: true, select: true });
        setSelection(node.firstChild, 1);
        await insertText(editor, "/");
        await insertText(editor, "link");
        // Todo: To remove when fuzzy search is merged.
        // Scenario : when we search /link in knowledge Article appears in the top result and then link.
        triggerHotkey("ArrowDown");
        await nextTick();
        triggerEvent(editor.editable, "keydown", { key: "Enter" });
        await nextTick();
        await inputText('input[id="o_link_dialog_label_input"]', 'link');
        await inputText('input[id="o_link_dialog_url_input"]', '#');
        editor.document.querySelector('.o_dialog footer button.btn-primary').click();
        await nextTick();
        editor.document.getSelection().collapseToEnd();
        triggerEvent(node, "keydown", { key: "Enter", shiftKey: true });
        assert.strictEqual(editable.innerHTML, `<p><a href="#" target="_blank" class="" contenteditable="true">link<br></a><br></p>`);
        // Todo: to change this assert to this when this task will be merged. (task-3446357)
        // assert.strictEqual(editable.innerHTML, `<p>a<a href="#" target="_blank" class="" contenteditable="true">lin<br>k</a>b</p>`)
        await nextTick();
    });
});
