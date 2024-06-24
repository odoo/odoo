import { closestBlock } from "@html_editor/utils/blocks";
import { childNodeIndex, endPos } from "@html_editor/utils/position";
import { findInSelection } from "@html_editor/utils/selection";
import { click, manuallyDispatchProgrammaticEvent, waitFor } from "@odoo/hoot-dom";
import { tick } from "@odoo/hoot-mock";
import { setSelection } from "./selection";

/** @typedef {import("@html_editor/plugin").Editor} Editor */

/**
 * @param {Editor} editor
 * @param {string} text
 */
export function insertText(editor, text) {
    const insertChar = (char) => {
        // Create and dispatch events to mock text insertion. Unfortunatly, the
        // events will be flagged `isTrusted: false` by the browser, requiring
        // the editor to detect them since they would not trigger the default
        // browser behavior otherwise.
        const range = editor.document.getSelection().getRangeAt(0);
        let offset = range.startOffset;
        let node = range.startContainer;

        if (node.nodeType !== Node.TEXT_NODE) {
            node = document.createTextNode(char);
            offset = 1;
            range.startContainer.appendChild(node);
            range.insertNode(node);
            setSelection({ anchorNode: node, anchorOffset: offset });
        } else {
            node.textContent =
                node.textContent.slice(0, offset) + char + node.textContent.slice(offset);
            offset++;
            setSelection({
                anchorNode: node,
                anchorOffset: offset,
            });
        }
    };
    for (const char of text) {
        // KeyDownEvent is required to trigger deleteRange.
        manuallyDispatchProgrammaticEvent(editor.editable, "keydown", { key: char });
        // InputEvent is required to simulate the insert text.
        insertChar(char);
        manuallyDispatchProgrammaticEvent(editor.editable, "input", {
            inputType: "insertText",
            data: char,
        });
        // KeyUpEvent is not required but is triggered like the browser would.
        manuallyDispatchProgrammaticEvent(editor.editable, "keyup", { key: char });
    }
}

/** @param {Editor} editor */
export function deleteForward(editor) {
    editor.dispatch("DELETE_FORWARD");
}

/**
 * @param {Editor} editor
 * @param {boolean} [isMobileTest=false]
 */
export function deleteBackward(editor, isMobileTest = false) {
    // TODO phoenix: find a strategy for test mobile and desktop. (check legacy code)

    editor.dispatch("DELETE_BACKWARD");
}

// history
/** @param {Editor} editor */
export function addStep(editor) {
    editor.dispatch("ADD_STEP");
}
/** @param {Editor} editor */
export function undo(editor) {
    editor.dispatch("HISTORY_UNDO");
}
/** @param {Editor} editor */
export function redo(editor) {
    editor.dispatch("HISTORY_REDO");
}

// list
export function toggleOrderedList(editor) {
    editor.dispatch("TOGGLE_LIST", { mode: "OL" });
}
/** @param {Editor} editor */
export function toggleUnorderedList(editor) {
    editor.dispatch("TOGGLE_LIST", { mode: "UL" });
}
/** @param {Editor} editor */
export function toggleCheckList(editor) {
    editor.dispatch("TOGGLE_LIST", { mode: "CL" });
}

/**
 * Clicks on the checkbox of a checklist item.
 *
 * @param {HTMLLIElement} li
 * @throws {Error} If the provided element is not a LI element within a checklist.
 */
export function clickCheckbox(li) {
    if (li.tagName !== "LI" || !li.parentNode.classList.contains("o_checklist")) {
        throw new Error("Expected a LI element in a checklist");
    }
    const liRect = li.getBoundingClientRect();
    click(li, { position: { clientX: liRect.left - 10, clientY: liRect.top + 10 } });
}

/** @param {Editor} editor */
export function insertLineBreak(editor) {
    editor.dispatch("INSERT_LINEBREAK");
}

// Format commands

/** @param {Editor} editor */
export function bold(editor) {
    editor.dispatch("FORMAT_BOLD");
}
/** @param {Editor} editor */
export function italic(editor) {
    editor.dispatch("FORMAT_ITALIC");
}
/** @param {Editor} editor */
export function underline(editor) {
    editor.dispatch("FORMAT_UNDERLINE");
}
/** @param {Editor} editor */
export function strikeThrough(editor) {
    editor.dispatch("FORMAT_STRIKETHROUGH");
}
export function setFontSize(size) {
    return (editor) => editor.dispatch("FORMAT_FONT_SIZE", { size });
}
/** @param {Editor} editor */
export function switchDirection(editor) {
    return editor.dispatch("SWITCH_DIRECTION");
}
/** @param {Editor} editor */
export function splitBlock(editor) {
    editor.dispatch("SPLIT_BLOCK");
}

// TODO @phoenix: we should maybe use it in each test ???
// Simulates placing the cursor at the editable root after an arrow key press
export async function simulateArrowKeyPress(editor, key) {
    const selection = editor.document.getSelection();
    const node = selection.anchorNode;
    let editableChild = node;
    while (editableChild.parentNode !== editor.editable) {
        editableChild = editableChild.parentNode;
    }
    const index =
        key === "ArrowRight" ? childNodeIndex(editableChild) + 1 : childNodeIndex(editableChild);
    const pos = [editor.editable, index];
    manuallyDispatchProgrammaticEvent(editor.editable, "keydown", { key });
    selection.setBaseAndExtent(...pos, ...pos);
    await tick();
}

export function unlinkByCommand(editor) {
    editor.dispatch("REMOVE_LINK_FROM_SELECTION");
}

export async function unlinkFromToolbar() {
    await waitFor(".o-we-toolbar");
    click(".btn[name='unlink']");
}

export async function unlinkFromPopover() {
    await waitFor(".o-we-linkpopover");
    click(".o_we_remove_link");
}

/** @param {Editor} editor */
export function keydownTab(editor) {
    manuallyDispatchProgrammaticEvent(editor.editable, "keydown", { key: "Tab" });
}
/** @param {Editor} editor */
export function keydownShiftTab(editor) {
    manuallyDispatchProgrammaticEvent(editor.editable, "keydown", { key: "Tab", shiftKey: true });
}
/** @param {Editor} editor */
export function resetSize(editor) {
    const selection = editor.shared.getEditableSelection();
    editor.dispatch("RESET_SIZE", { table: findInSelection(selection, "table") });
}
/** @param {Editor} editor */
export function justifyLeft(editor) {
    editor.dispatch("JUSTIFY_LEFT");
}
/** @param {Editor} editor */
export function justifyCenter(editor) {
    editor.dispatch("JUSTIFY_CENTER");
}
/** @param {Editor} editor */
export function justifyRight(editor) {
    editor.dispatch("JUSTIFY_RIGHT");
}
/** @param {Editor} editor */
export function justifyFull(editor) {
    editor.dispatch("JUSTIFY_FULL");
}

/**
 * @param {string} color
 * @param {string} mode
 */
export function setColor(color, mode) {
    /** @param {Editor} editor */
    return (editor) => {
        editor.dispatch("APPLY_COLOR", { color, mode });
    };
}

// Mock an paste event and send it to the editor.

/**
 * @param {Editor} editor
 * @param {string} text
 * @param {string} type
 */
function pasteData(editor, text, type) {
    const clipboardData = new DataTransfer();
    clipboardData.setData(type, text);
    const pasteEvent = new ClipboardEvent("paste", { clipboardData, bubbles: true });
    editor.editable.dispatchEvent(pasteEvent);
}
/**
 * @param {Editor} editor
 * @param {string} text
 */
export function pasteText(editor, text) {
    return pasteData(editor, text, "text/plain");
}
/**
 * @param {Editor} editor
 * @param {string} html
 */
export function pasteHtml(editor, html) {
    return pasteData(editor, html, "text/html");
}
/**
 * @param {Editor} editor
 * @param {string} html
 */
export function pasteOdooEditorHtml(editor, html) {
    return pasteData(editor, html, "application/vnd.odoo.odoo-editor");
}
/**
 * @param {Node} node
 */
export async function tripleClick(node) {
    const anchorNode = node;
    node = node.nodeType === Node.ELEMENT_NODE ? node : node.parentNode;
    manuallyDispatchProgrammaticEvent(node, "mousedown", { detail: 3 });
    let focusNode = closestBlock(anchorNode).nextSibling;
    let focusOffset = 0;
    if (!focusNode) {
        [focusNode, focusOffset] = endPos(anchorNode);
    }
    setSelection({
        anchorNode,
        anchorOffset: 0,
        focusNode,
        focusOffset,
    });
    manuallyDispatchProgrammaticEvent(node, "mouseup", { detail: 3 });
    manuallyDispatchProgrammaticEvent(node, "click", { detail: 3 });

    await tick();
}
