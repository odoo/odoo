import { afterEach, beforeEach, expect, queryFirst } from "@odoo/hoot";
import { waitUntil } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { getSelectionInTree } from "@html_editor/utils/selection";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { deleteBackward, insertLineBreak } from "@html_editor/../tests/_helpers/user_actions";

import { contains, focus, TIMEOUT } from "@mail/../tests/mail_test_helpers_contains";
import { htmlInsertText } from "@mail/../tests/mail_test_helpers_html";

/** @type {Map<import("@odoo/owl").Signal<Element>, import("@html_editor/editor").Editor>} */
let composerRootRefToEditor;
beforeEach(() => (composerRootRefToEditor = new Map()));
afterEach(() => composerRootRefToEditor.clear());

export function _addRootRefToEditor(rootRef, editor) {
    composerRootRefToEditor.set(rootRef, editor);
}

/**
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @returns {import("@odoo/owl").Signal<Element> | undefined}
 */
function findComposerRootRef(selector) {
    const el = queryFirst(selector);
    if (!el) {
        return;
    }
    const rootRefs = [...composerRootRefToEditor.keys()].filter(
        (rootRef) => !composerRootRefToEditor.get(rootRef).isDestroyed && rootRef()?.contains(el)
    );
    // innermost composer, e.g. the one of a message being edited
    return rootRefs.find((rootRef) =>
        rootRefs.every((other) => other === rootRef || !rootRef().contains(other()))
    );
}

/**
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @returns {import("@html_editor/editor").Editor}
 */
export function getEditorFromComposerEl(selector) {
    const rootRef = findComposerRootRef(selector);
    if (rootRef) {
        return composerRootRefToEditor.get(rootRef);
    }
}

/**
 * Waits for the editor of the composer to be ready, and returns it.
 *
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @returns {Promise<import("@html_editor/editor").Editor>}
 */
export async function waitForComposerEditor(selector) {
    await contains(selector);
    const waitForReadyEditor = () =>
        waitUntil(
            () => {
                const editor = getEditorFromComposerEl(selector);
                return editor?.isReady && editor.editable.isConnected && editor;
            },
            {
                message: `Composer editor of "${selector}" not ready after %timeout% milliseconds`,
                timeout: TIMEOUT,
            }
        );
    await waitForReadyEditor();
    // let the composer settle (e.g. auto-focus, selection sync), which may re-render it
    await animationFrame();
    return waitForReadyEditor();
}

/**
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {string} text "\n" inserts a line break
 * @param {Object} [options]
 * @param {boolean} [options.replace=false] whether to clear the content first
 */
export async function insertTextInComposer(selector, text, { replace = false } = {}) {
    const editor = await waitForComposerEditor(selector);
    await focus(editor.editable);
    if (replace) {
        let paragraph = editor.editable.querySelector("div.o-paragraph");
        while (paragraph.textContent.length) {
            // select the whole paragraph (tripleClick is not supported on mobile)
            setSelection({
                anchorNode: paragraph,
                anchorOffset: 0,
                focusNode: paragraph,
                focusOffset: paragraph.childNodes.length,
            });
            await animationFrame();
            deleteBackward(editor);
            paragraph = editor.editable.querySelector("div.o-paragraph");
        }
    }
    // "\n" inserts a line break, as Shift+Enter does in the composer.
    const [firstLine, ...otherLines] = text.split("\n").map(preserveConsecutiveSpaces);
    await htmlInsertText(editor, firstLine);
    for (const line of otherLines) {
        insertLineBreak(editor);
        await animationFrame(); // wait for mail composer state synced with new value
        await htmlInsertText(editor, line);
    }
}

/**
 * Replace consecutive spaces by alternating nbsp, like the browser does when
 * typing them, otherwise they are collapsed (and removed next to line breaks).
 *
 * @param {string} text
 */
function preserveConsecutiveSpaces(text) {
    return text.replace(/ {2,}/g, (spaces) =>
        [...spaces].map((_, i) => (i % 2 === 0 ? "\u00a0" : " ")).join("")
    );
}

/**
 * Waits until the composer contains exactly the given text.
 *
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {string} text
 */
export async function containsTextInComposer(selector, text) {
    await contains(selector);
    let editor;
    // The editor is fetched on each check, as a re-render of the composer replaces it.
    await waitUntil(
        () => {
            editor = getEditorFromComposerEl(selector);
            return (
                editor?.isReady &&
                editor.editable.isConnected &&
                editor.editable.textContent === text
            );
        },
        {
            message: () =>
                `Composer "${selector}" does not contain ${JSON.stringify(
                    text
                )} after %timeout% milliseconds (content: ${JSON.stringify(
                    editor?.editable?.textContent
                )})`,
            timeout: TIMEOUT,
        }
    );
    // No text option: `contains` trims it, while the exact text was checked above.
    return contains(".o-mail-Composer-html", { target: findComposerRootRef(selector)() });
}

/**
 * Set selection of the composer text to 'start' and 'end' values.
 *
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {Object} param1
 * @param {number} param1.start
 * @param {number} param1.end
 */
export async function setSelectionInComposer(selector, { start, end }) {
    const editor = await waitForComposerEditor(selector);
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
 * @param {import("@odoo/hoot-dom").Target} selector the composer root or any element inside it
 * @param {Object} param1
 * @param {number} param1.start
 * @param {number} param1.end
 */
export async function containsSelectionInComposer(selector, { start, end }) {
    const editor = await waitForComposerEditor(selector);
    const paragraph = editor.editable.querySelector(".o-paragraph");
    const selection = getSelectionInTree(editor.editable);
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
                currentEnd += selection.focusOffset;
                break;
            }
            currentEnd += paragraph.childNodes[i].textContent.length;
        }
    }
    expect(currentStart).toBe(start);
    expect(currentEnd).toBe(end);
}
