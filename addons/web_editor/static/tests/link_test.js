/** @odoo-module **/
import { setSelection } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { patchWithCleanup, nextTick } from "@web/../tests/helpers/utils";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import {
    triggerEvent,
    insertText,
    insertParagraphBreak,
} from "@web_editor/js/editor/odoo-editor/test/utils";

function onMount() {
    const editor = wysiwyg.odooEditor;
    const editable = editor.editable;
    editor.testMode = true;
    return { editor, editable };
}

function inputText(selector, content, { replace = false } = {}) {
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

QUnit.module(
    "web_editor",
    {
        before: function () {
            serverData = {
                models: {
                    note: {
                        fields: {
                            body: {
                                string: "Editor",
                                type: "html",
                            },
                        },
                        records: [
                            {
                                id: 1,
                                display_name: "first record",
                                body: "<p><br></p>",
                            },
                        ],
                    },
                },
            };
        },
        beforeEach: async function () {
            setupViewRegistries();
            patchWithCleanup(Wysiwyg.prototype, {
                init() {
                    super.init(...arguments);
                    wysiwyg = this;
                },
            });
            await makeView({
                type: "form",
                serverData,
                resModel: "note",
                arch:
                    "<form>" +
                    '<field name="body" widget="html" style="height: 100px"/>' +
                    "</form>",
                resId: 1,
            });
        },
    },
    function () {
        QUnit.module("HotKeys");

        QUnit.test("should be able to create link with ctrl+k", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            triggerEvent(node, "keydown", {
                key: "K",
                ctrlKey: true,
            });
            await nextTick();
            inputText(".o_command_palette_search", "k");
            await nextTick();
            triggerEvent(node, "keydown", {
                key: "Enter",
            });
            await nextTick();
            inputText('input[id="o_link_dialog_url_input"]', "#");
            editor.document.querySelector(".o_dialog footer button.btn-primary").click();
            assert.strictEqual(
                editable.innerHTML,
                '<p><a href="#" target="_blank" class="" contenteditable="true">#</a><br></p>'
            );
        });

        QUnit.test(
            "should be able to create link with ctrl+k , and should make link on two existing characters",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                insertText(editor, "Hello");
                setSelection(node, 1, node, 3);
                triggerEvent(node, "keydown", {
                    key: "K",
                    ctrlKey: true,
                });
                await nextTick();
                inputText(".o_command_palette_search", "k");
                await nextTick();
                triggerEvent(node, "keydown", {
                    key: "Enter",
                });
                await nextTick();
                inputText('input[id="o_link_dialog_url_input"]', "#");
                editor.document.querySelector(".o_dialog footer button.btn-primary").click();
                assert.strictEqual(
                    editable.innerHTML,
                    '<p>H<a href="#" target="_blank" class="" contenteditable="true">el</a>lo</p>'
                );
                await nextTick();
            }
        );


        QUnit.module("Typing based");

        QUnit.test("typing www.odoo.com + space should convert to link", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            inputText(".odoo-editor-editable p", "www.odoo.com");
            insertText(editor, " ");
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                '<p><a href="http://www.odoo.com">www.odoo.com</a> </p>'
            );
        });

        QUnit.test("typing odoo.com + space should convert to link", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            inputText(".odoo-editor-editable p", "odoo.com");
            insertText(editor, " ");
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                '<p><a href="http://odoo.com">odoo.com</a> </p>'
            );
        });

        QUnit.test(
            "typing http://odoo.com + space should convert to link",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", "http://odoo.com");
                insertText(editor, " ");
                await nextTick();
                assert.strictEqual(
                    editable.innerHTML,
                    '<p><a href="http://odoo.com">http://odoo.com</a> </p>'
                );
            }
        );

        QUnit.test(
            "typing http://google.co.in + space should convert to link",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", "http://google.co.in");
                insertText(editor, " ");
                await nextTick();
                assert.strictEqual(
                    editable.innerHTML,
                    '<p><a href="http://google.co.in">http://google.co.in</a> </p>'
                );
            }
        );

        QUnit.test("typing www.odoo + space should not convert to link", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            inputText(".odoo-editor-editable p", "www.odoo");
            insertText(editor, " ");
            await nextTick();
            assert.strictEqual(editable.innerHTML, "<p>www.odoo </p>");
        });


        QUnit.module("Toolbar based");

        QUnit.test("should convert all selected text to link", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "Hello");
            triggerEvent(node, "keydown", { key: "a", ctrlKey: true });
            await nextTick();
            editor.document.querySelector(".fa-link").click();
            await nextTick();
            inputText('input[id="o_link_dialog_url_input"]', "#");
            editor.document.querySelector(".o_dialog footer button.btn-primary").click();
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                '<p><a href="#" target="_blank" class="" contenteditable="true">Hello</a></p>'
            );
        });

        QUnit.test("should set the link on two existing characters", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "Hello");
            setSelection(node, 1, node, 3);
            editor.document.querySelector(".fa-link").click();
            await nextTick();
            inputText('input[id="o_link_dialog_url_input"]', "#");
            editor.document.querySelector(".o_dialog footer button.btn-primary").click();
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                '<p>H<a href="#" target="_blank" class="" contenteditable="true">el</a>lo</p>'
            );
        });

        QUnit.test("Should be able to insert link on empty p", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            triggerEvent(node, "keydown", { key: "a", ctrlKey: true });
            await nextTick();
            editor.document.querySelector(".fa-link").click();
            await nextTick();
            inputText('input[id="o_link_dialog_url_input"]', "#");
            editor.document.querySelector(".o_dialog footer button.btn-primary").click();
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                '<p><a href="#" target="_blank" class="" contenteditable="true"><br></a></p>'
            );
        });


        QUnit.module("PowerBox related");

        QUnit.test("should insert a link and preserve spacing", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            inputText(".odoo-editor-editable p", "a     b");
            setSelection(node.firstChild, 3, node.firstChild, 3);
            triggerEvent(node, "input", { data: "/" });
            editor.document.querySelector(".oe-powerbox-commandWrapper .fa-link").click();
            await nextTick();
            triggerEvent(node, "keydown", { key: "Enter" });
            await nextTick();
            inputText('input[id="o_link_dialog_label_input"]', "link");
            inputText('input[id="o_link_dialog_url_input"]', "#");
            editor.document.querySelector(".o_dialog footer button.btn-primary").click();
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                `<p>a&nbsp; <a href="#" target="_blank" class="" contenteditable="true">link</a>&nbsp; &nbsp;b</p>`
            );
        });

        QUnit.test(
            "should insert a link and write a character after the link is created",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", `ab`);
                setSelection(node.firstChild, 1);
                triggerEvent(node, "input", { data: "/" });
                editor.document.querySelector(".oe-powerbox-commandWrapper .fa-link").click();
                await nextTick();
                triggerEvent(editor.editable, "keydown", { key: "Enter" });
                await nextTick();
                inputText('input[id="o_link_dialog_url_input"]', "#");
                editor.document.querySelector(".o_dialog footer button.btn-primary").click();
                await nextTick();
                editor.document.getSelection().collapseToEnd();
                insertText(editor, "D");
                assert.strictEqual(
                    editable.innerHTML,
                    `<p>a<a href="#" target="_blank" class="" contenteditable="true">#D</a>b</p>`
                );
            }
        );

        QUnit.test(
            "should insert a link and write 2 character after the link is created",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", `ab`);
                setSelection(node.firstChild, 1);
                triggerEvent(node, "input", { data: "/" });
                editor.document.querySelector(".oe-powerbox-commandWrapper .fa-link").click();
                await nextTick();
                triggerEvent(editor.editable, "keydown", { key: "Enter" });
                await nextTick();
                inputText('input[id="o_link_dialog_url_input"]', "#");
                editor.document.querySelector(".o_dialog footer button.btn-primary").click();
                await nextTick();
                editor.document.getSelection().collapseToEnd();
                insertText(editor, "E");
                insertText(editor, "D");
                assert.strictEqual(
                    editable.innerHTML,
                    `<p>a<a href="#" target="_blank" class="" contenteditable="true">#ED</a>b</p>`
                );
            }
        );

        QUnit.test(
            "should insert a link and write a character after the link then create a new <p>",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", `ab`);
                triggerEvent(node, "input", { data: "/" });
                editor.document.querySelector(".oe-powerbox-commandWrapper .fa-link").click();
                await nextTick();
                triggerEvent(editor.editable, "keydown", { key: "Enter" });
                await nextTick();
                inputText('input[id="o_link_dialog_label_input"]', "link");
                inputText('input[id="o_link_dialog_url_input"]', "#");
                editor.document.querySelector(".o_dialog footer button.btn-primary").click();
                await nextTick();
                editor.document.getSelection().collapseToEnd();
                insertText(editor, "E");
                await insertParagraphBreak(editor);
                assert.strictEqual(
                    editable.innerHTML,
                    `<p>ab<a href="#" target="_blank" class="" contenteditable="true">linkE</a></p><p><br></p>`
                );
            }
        );

        QUnit.test(
            "should insert a link, write a character, a new <p>, and another character",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", `ab`);
                setSelection(node.firstChild, 1);
                triggerEvent(node, "input", { data: "/" });
                editor.document.querySelector(".oe-powerbox-commandWrapper .fa-link").click();
                await nextTick();
                triggerEvent(editor.editable, "keydown", { key: "Enter" });
                await nextTick();
                inputText('input[id="o_link_dialog_label_input"]', "link");
                inputText('input[id="o_link_dialog_url_input"]', "#");
                editor.document.querySelector(".o_dialog footer button.btn-primary").click();
                await nextTick();
                editor.document.getSelection().collapseToEnd();
                insertText(editor, "E");
                await insertParagraphBreak(editor);
                insertText(editor, "D");
                assert.strictEqual(
                    editable.innerHTML,
                    `<p>a<a href="#" target="_blank" class="" contenteditable="true">linkE</a></p>D<p>b</p>`
                );
            }
        );

        QUnit.test(
            "should insert a link and write a character at the end of the link then insert a <br>",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", `ab`);
                setSelection(node.firstChild, 1);
                triggerEvent(node, "input", { data: "/" });
                editor.document.querySelector(".oe-powerbox-commandWrapper .fa-link").click();
                await nextTick();
                triggerEvent(editor.editable, "keydown", { key: "Enter" });
                await nextTick();
                inputText('input[id="o_link_dialog_label_input"]', "link");
                inputText('input[id="o_link_dialog_url_input"]', "#");
                editor.document.querySelector(".o_dialog footer button.btn-primary").click();
                await nextTick();
                editor.document.getSelection().collapseToEnd();
                insertText(editor, "E");
                triggerEvent(node, "keydown", { key: "Enter", shiftKey: true });
                assert.strictEqual(
                    editable.innerHTML,
                    `<p>a<a href="#" target="_blank" class="" contenteditable="true">linkE<br></a>b</p>`
                );
                await nextTick();
            }
        );

        QUnit.test(
            "should insert a link and write a character insert a <br> and another character",
            async function (assert) {
                const { editor, editable } = onMount();
                const node = editable.querySelector("p");
                setSelection(node, 0);
                inputText(".odoo-editor-editable p", `ab`);
                setSelection(node.firstChild, 1);
                triggerEvent(node, "input", { data: "/" });
                editor.document.querySelector(".oe-powerbox-commandWrapper .fa-link").click();
                await nextTick();
                triggerEvent(node, "keydown", { key: "Enter" });
                await nextTick();
                inputText('input[id="o_link_dialog_label_input"]', "link");
                inputText('input[id="o_link_dialog_url_input"]', "#");
                editor.document.querySelector(".o_dialog footer button.btn-primary").click();
                await nextTick();
                editor.document.getSelection().collapseToEnd();
                insertText(editor, "E");
                triggerEvent(node, "keydown", { key: "Enter", shiftKey: true });
                insertText(editor, "D");
                assert.strictEqual(
                    editable.innerHTML,
                    `<p>a<a href="#" target="_blank" class="" contenteditable="true">linkE<br>D</a>b</p>`
                );
                await nextTick();
            }
        );
    }
);
