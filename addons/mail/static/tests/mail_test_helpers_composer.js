import { afterEach, beforeEach, expect, queryFirst } from "@odoo/hoot";

import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { deleteBackward, tripleClick } from "@html_editor/../tests/_helpers/user_actions";

import { contains, focus } from "@mail/../tests/mail_test_helpers_contains";
import { htmlInsertText } from "@mail/../tests/mail_test_helpers_html";

/** @type {Map<import("@odoo/owl").Signal<Element>, import("@html_editor/editor").Editor>} */
let composerRootRefToEditor;
beforeEach(() => (composerRootRefToEditor = new Map()));
afterEach(() => composerRootRefToEditor.clear());

export function _addRootRefToEditor(rootRef, editor) {
    composerRootRefToEditor.set(rootRef, editor);
}

export function _clearRootRefToEditor() {
    composerRootRefToEditor.clear();
}

/**
 * @param {import("@odoo/hoot-dom").Target} selector
 * @returns {import("@html_editor/editor").Editor}
 */
export function getEditorFromComposerEl(selector) {
    const composerRootEl = queryFirst(selector);
    const key = [...composerRootRefToEditor.keys()].find(
        (rootRef) => rootRef() === composerRootEl || rootRef()?.contains(composerRootEl)
    );
    if (key) {
        return composerRootRefToEditor.get(key);
    }
}

export async function insertTextInComposer(selector, text, { replace = false } = {}) {
    await contains(`${selector}-html`);
    const editor = getEditorFromComposerEl(selector);
    await focus(editor.editable);
    if (replace) {
        let paragraph = editor.editable.querySelector("div.o-paragraph");
        while (paragraph.textContent.length) {
            await tripleClick(paragraph);
            deleteBackward(editor);
            paragraph = editor.editable.querySelector("div.o-paragraph");
        }
    }
    return htmlInsertText(editor, text);
}

export async function containsTextInComposer(selector, text) {
    return contains(`${selector}-html`, { textContent: text });
}

/**
 * Set selection of the composer text to 'start' and 'end' values.
 *
 * @param {string} selector The selector of composer's root el
 * @param {Object} param1
 * @param {number} param1.start
 * @param {number} param1.end
 */
export async function setSelectionInComposer(selector, { start, end }) {
    await contains(selector);
    const editor = getEditorFromComposerEl(selector);
    const paragraph = editor.editable.querySelector(".o-paragraph");
    // /!\ This assumes anchor / focus nodes are flat on paragraph /!\
    let charIndexFromAnchor = 0;
    let anchorNode, anchorOffset;
    for (let i = 0; i < paragraph.childNodes.length; i++) {
        const childNode = paragraph.childNodes[i];
        const childTextContentLength = childNode.textContent.length;
        if (charIndexFromAnchor + childTextContentLength < start) {
            charIndexFromAnchor += childTextContentLength;
            continue;
        }
        anchorNode = childNode;
        anchorOffset = start - charIndexFromAnchor;
        break;
    }
    let charIndexFromFocus = 0;
    let focusNode, focusOffset;
    for (let i = 0; i < paragraph.childNodes.length; i++) {
        const childNode = paragraph.childNodes[i];
        const childTextContentLength = childNode.textContent.length;
        if (charIndexFromFocus + childTextContentLength < end) {
            charIndexFromFocus += childTextContentLength;
            continue;
        }
        focusNode = childNode;
        focusOffset = end - charIndexFromFocus;
        break;
    }
    setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
}

/**
 * Determine whether the composer text has given selection 'start' and 'end'
 *
 * @param {string} selector The selector of composer's root el
 * @param {Object} param1
 * @param {number} param1.start
 * @param {number} param1.end
 */
export async function containsSelectionInComposer(selector, { start, end }) {
    await contains(selector);
    const editor = getEditorFromComposerEl(selector);
    const paragraph = editor.editable.querySelector(".o-paragraph");
    const selection = document.getSelection();
    let currentStart = 0;
    let currentEnd = 0;
    if (selection.anchorNode === paragraph) {
        const toIndex = selection.anchorOffset;
        for (let i = 0; i < toIndex; i++) {
            currentStart += paragraph.childNodes[i].textContent.length;
        }
    } else {
        // /!\ This assumes anchor / focus nodes are flat on paragraph /!\
        const anchorNodeIndex = Array.prototype.findIndex.call(
            paragraph.childNodes,
            (n) => n === selection.anchorNode
        );
        if (anchorNodeIndex === -1) {
            throw new Error("Selection's anchor node is not inside this composer");
        }
        for (let i = 0; i < paragraph.childNodes.length; i++) {
            if (i == anchorNodeIndex) {
                currentStart += selection.anchorOffset;
                break;
            }
            currentStart += paragraph.childNodes[i].textContent.length;
        }
    }
    if (selection.focusNode === paragraph) {
        const toIndex = selection.focusOffset;
        for (let i = 0; i < toIndex; i++) {
            currentEnd += paragraph.childNodes[i].textContent.length;
        }
    } else {
        const focusNodeIndex = Array.prototype.findIndex.call(
            paragraph.childNodes,
            (n) => n === selection.focusNode
        );
        if (focusNodeIndex === -1) {
            throw new Error("Selection's focus node is not inside this composer");
        }
        for (let i = 0; i < paragraph.childNodes.length; i++) {
            if (i == focusNodeIndex) {
                currentEnd += selection.focusNode.textContent.length;
                break;
            }
            currentEnd += paragraph.childNodes[i];
        }
    }
    expect(currentStart).toBe(start);
    expect(currentEnd).toBe(end);
}
