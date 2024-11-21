/** @odoo-module **/
import { setSelection } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { patchWithCleanup, nextTick } from "@web/../tests/helpers/utils";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import {
    triggerEvent,
    insertText,
} from "@web_editor/js/editor/odoo-editor/test/utils";

function onMount() {;
    const editor = wysiwyg.odooEditor;
    const editable = editor.editable;
    editor.testMode = true;
    return { editor, editable };
}

let wysiwyg;

QUnit.module(
    "web_editor",
    {
        beforeEach: async function () {
            const serverData = {
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
                    '<field name="body" widget="html_legacy" style="height: 100px"/>' +
                    "</form>",
                resId: 1,
            });
        },
    },
    function () {

        QUnit.module("insert a new banner");
        QUnit.test("should insert a banner followed by a paragraph", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "Test");
            setSelection(node.firstChild, 3, node.firstChild, 3);
            insertText(editor, '/banner');
            triggerEvent(editor.editable, "keydown", { key: "Enter" });
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                `<p>Test</p><div class="o_editor_banner o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" data-oe-protected="true" contenteditable="false">
                        <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                        <div class="w-100 px-3" data-oe-protected="false" contenteditable="true">
                            <p placeholder=\"Type &quot;/&quot; for commands\" class=\"oe-hint oe-command-temporary-hint\"><br></p>
                        </div>
                    </div><p><br></p>`,
            );
        });
        QUnit.test("should have focus inside banner when new banner is created", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "Test");
            setSelection(node.firstChild, 3, node.firstChild, 3);
            insertText(editor, '/banner');
            triggerEvent(editor.editable, "keydown", { key: "Enter" });
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                `<p>Test</p><div class="o_editor_banner o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" data-oe-protected="true" contenteditable="false">
                        <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                        <div class="w-100 px-3" data-oe-protected="false" contenteditable="true">
                            <p placeholder=\"Type &quot;/&quot; for commands\" class=\"oe-hint oe-command-temporary-hint\"><br></p>
                        </div>
                    </div><p><br></p>`,
            );
        });

        QUnit.module("banner selection and backspace");
        QUnit.test("preserves the first paragraph tag inside the banner", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "Test");
            setSelection(node.firstChild, 3, node.firstChild, 3);
            insertText(editor, '/banner');
            triggerEvent(editor.editable, "keydown", { key: "Enter" });
            await nextTick();
            insertText(editor, 'Test1');
            triggerEvent(editor.editable, "input", { inputType: "insertParagraph" });
            insertText(editor, 'Test2');
            triggerEvent(editor.editable, "input", { inputType: "insertParagraph" });
            triggerEvent(editor.editable, "keydown", { key: "a", ctrlKey: true });
            await nextTick();
            triggerEvent(editor.editable, "input", { inputType: "deleteContentBackward" });
            assert.strictEqual(
                editable.innerHTML,
                `<p>Test</p><div class="o_editor_banner o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" data-oe-protected="true" contenteditable="false">
                        <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                        <div class="w-100 px-3" data-oe-protected="false" contenteditable="true">
                            <p placeholder=\"Type &quot;/&quot; for commands\" class=\"oe-hint oe-command-temporary-hint\"><br></p></div>
                    </div><p><br></p>`,
            );
        });
        QUnit.test("First element of o_editable is not editable", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, '/banner');
            triggerEvent(editor.editable, "keydown", { key: "Enter" });
            await nextTick();
            const p = editable.querySelectorAll('p')[1];
            setSelection(p, 0);
            insertText(editor, 'Test1');
            triggerEvent(editor.editable, "input", { inputType: "insertParagraph" });
            insertText(editor, 'Test2');
            triggerEvent(editor.editable, "keydown", { key: "a", ctrlKey: true });
            await nextTick();
            triggerEvent(editor.editable, "input", { inputType: "deleteContentBackward" });
            await nextTick();
            assert.strictEqual(
                editable.innerHTML,
                `<p placeholder=\"Type &quot;/&quot; for commands\" class=\"oe-hint oe-command-temporary-hint\"><br></p>`,
                "should remove banner when ctrl+a and backspace are performed",
            );
        });
    }
);
