import { animationFrame } from "@odoo/hoot-mock";
import { insertText as htmlEditorInsertText } from "@html_editor/../tests/_helpers/user_actions";

/**
 * Simulates text insertion in the html composer editor.
 *
 * @param {{ document: Document, editable: HTMLElement }} editor
 * @param {string} text
 */
export async function htmlInsertText(editor, text) {
    await htmlEditorInsertText(editor, text);
    await animationFrame(); // wait for mail composer state synced with new value
}
