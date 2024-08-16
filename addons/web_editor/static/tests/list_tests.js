import { setSelection } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { insertText, triggerEvent, unformat } from "@web_editor/js/editor/odoo-editor/test/utils";

function onMount() {
    const editor = wysiwyg.odooEditor;
    const editable = editor.editable;
    editor.testMode = true;
    return { editor, editable };
}

let serverData;
let wysiwyg;

QUnit.module(
    "Automatic list creation based on typing",
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
                    '<field name="body" widget="html_legacy" style="height: 100px"/>' +
                    "</form>",
                resId: 1,
            });
        },
    },
    function () {
        QUnit.module("Creating a numbered lists via typing");

        QUnit.test("typing '1. ' should create number list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "1. ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol><li><br></li></ol>`,
            );
        });

        QUnit.test("typing '1) ' should create number list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "1) ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol><li><br></li></ol>`,
            );
        });

        QUnit.test("Typing '1. ' at the start of existing text should create a numbered list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "abc");
            setSelection(node, 0);
            insertText(editor, "1. ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol><li>abc</li></ol>`,
            );
        });

        QUnit.test("should convert simple number list into bullet list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, '1. ');
            insertText(editor, '/bulletedlist');
            await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ul><li><br></li></ul>`,
            );
        });

        QUnit.test("typing 'a. ' should create number list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor , "a. ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol style="list-style: lower-alpha;"><li><br></li></ol>`,
            );
        });

        QUnit.test("typing 'a) ' should create number list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "a) ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol style="list-style: lower-alpha;"><li><br></li></ol>`,
            );
        });

        QUnit.test("should convert lower-alpha list into bullet list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, 'a. ');
            insertText(editor, '/bulletedlist');
            await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ul><li><br></li></ul>`,
            );
        });

        QUnit.test("typing 'A. ' should create number list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "A. ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol style="list-style: upper-alpha;"><li><br></li></ol>`,
            );
        });

        QUnit.test("typing 'A) ' should create number list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "A) ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol style="list-style: upper-alpha;"><li><br></li></ol>`,
            );
        });

        QUnit.test("should convert upper-alpha list into bullet list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, 'A. ');
            insertText(editor, '/bulletedlist');
            await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ul><li><br></li></ul>`,
            );
        });

        QUnit.test("creating list directly inside table column (td)", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "/table");
            await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
            await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
            await triggerEvent(editor.editable, 'keydown', { key: 'Backspace' });
            insertText(editor, "A. ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                unformat(`
                    <table class="table table-bordered o_table">
                        <tbody>
                            <tr>
                                <td><ol style="list-style: upper-alpha;"><li><br></li></ol></td>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                        </tbody>
                    </table>
                    <p><br></p>`),
            );
        });

        QUnit.module("Creating a bullet lists via typing");

        QUnit.test("typing '* ' should create bullet list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "* ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ul><li><br></li></ul>`,
            );
        });

        QUnit.test("Typing '* ' at the start of existing text should create a bullet list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "abc");
            setSelection(node, 0);
            insertText(editor, "* ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ul><li>abc</li></ul>`,
            );
        });

        QUnit.test("typing '- ' should create bullet list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, "- ");
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ul><li><br></li></ul>`,
            );
        });

        QUnit.test("should convert a bullet list into a numbered list", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, '- ');
            insertText(editor, '/numberedlist');
            await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<ol><li><br></li></ol>`,
            );
        });

        QUnit.module("list should not be created");

        QUnit.test("List should not be created when typing '1. ' at the end or within the text", async function (assert) {
            const { editor, editable } = onMount();
            const node = editable.querySelector("p");
            setSelection(node, 0);
            insertText(editor, 'abc');
            insertText(editor, '1. ');
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<p>abc1. </p>`,
                'Typing "1. " at the end of the text',
            );
            setSelection(node, 1);
            insertText(editor, '1. ');
            editor.clean();
            assert.strictEqual(
                editable.innerHTML,
                `<p>a1. bc1. </p>`,
                'Typing "1. " in between the text',
            );
        });
    }
);
