import { OdooEditor } from '../src/OdooEditor.js';
import { sanitize } from '../src/utils/sanitize.js';
import { insertText as insertTextSel } from '../src/utils/utils.js';

const Direction = {
    BACKWARD: 'BACKWARD',
    FORWARD: 'FORWARD',
};

function _nextNode(node) {
    let next = node.firstChild || node.nextSibling;
    if (!next) {
        next = node;
        while (next.parentNode && !next.nextSibling) {
            next = next.parentNode;
        }
        next = next && next.nextSibling;
    }
    return next;
}

function _toDomLocation(node, index) {
    let container;
    let offset;
    if (node.textContent.length) {
        container = node;
        offset = index;
    } else {
        container = node.parentNode;
        offset = Array.from(node.parentNode.childNodes).indexOf(node);
    }
    return [container, offset];
}

export function parseTextualSelection(testContainer) {
    let anchorNode;
    let anchorOffset;
    let focusNode;
    let focusOffset;
    let direction = Direction.FORWARD;

    let node = testContainer;
    while (node && !(anchorNode && focusNode)) {
        let next;
        if (node.nodeType === Node.TEXT_NODE) {
            // Look for special characters in the text content and remove them.
            const anchorIndex = node.textContent.indexOf('[');
            node.textContent = node.textContent.replace('[', '');
            const focusIndex = node.textContent.indexOf(']');
            node.textContent = node.textContent.replace(']', '');

            // Set the nodes and offsets if we found the selection characters.
            if (anchorIndex !== -1) {
                [anchorNode, anchorOffset] = _toDomLocation(node, anchorIndex);
                // If the focus node has already been found by this point then
                // it is before the anchor node, so the selection is backward.
                if (focusNode) {
                    direction = Direction.BACKWARD;
                }
            }
            if (focusIndex !== -1) {
                [focusNode, focusOffset] = _toDomLocation(node, focusIndex);
                // If the anchor character is within the same parent and is
                // after the focus character, then the selection is backward.
                // Adapt the anchorOffset to account for the focus character
                // that was removed.
                if (anchorNode === focusNode && anchorOffset > focusOffset) {
                    direction = Direction.BACKWARD;
                    anchorOffset--;
                }
            }

            // Get the next node to check.
            next = _nextNode(node);

            // Remove the textual range node if it is empty.
            if (!node.textContent.length) {
                node.parentNode.removeChild(node);
            }
        } else {
            next = _nextNode(node);
        }
        node = next;
    }
    if (anchorNode && focusNode) {
        return {
            anchorNode: anchorNode,
            anchorOffset: anchorOffset,
            focusNode: focusNode,
            focusOffset: focusOffset,
            direction: direction,
        };
    }
}

export function parseMultipleTextualSelection(testContainer) {
    let currentNode = testContainer;

    const clients = {};
    while (currentNode) {
        if (currentNode.nodeType === Node.TEXT_NODE) {
            // Look for special characters in the text content and remove them.
            let match;
            const regex = new RegExp(/(?:\[(\w+)\})|(?:\{(\w+)])/, 'gd');
            while ((match = regex.exec(currentNode.textContent))) {
                regex.lastIndex = 0;
                const indexes = match.indices[0];

                if (match[0].includes('}')) {
                    const clientId = match[1];
                    clients[clientId] = clients[clientId] || {};
                    clients[clientId].anchorNode = currentNode;
                    clients[clientId].anchorOffset = indexes[0];
                    if (clients[clientId].focusNode) {
                        clients[clientId].direction = Direction.FORWARD;
                    }
                } else {
                    const clientId = match[2];
                    clients[clientId] = clients[clientId] || {};
                    clients[clientId].focusNode = currentNode;
                    clients[clientId].focusOffset = indexes[0];
                    if (clients[clientId].anchorNode) {
                        clients[clientId].direction = Direction.BACKWARD;
                    }
                }
                currentNode.textContent =
                    currentNode.textContent.slice(0, indexes[0]) +
                    currentNode.textContent.slice(indexes[1]);
            }
        }
        currentNode = _nextNode(currentNode);
    }

    return clients;
}

/**
 * Set a range in the DOM.
 *
 * @param selection
 */
export function setTestSelection(selection, doc = document) {
    const domRange = doc.createRange();
    if (selection.direction === Direction.FORWARD) {
        domRange.setStart(selection.anchorNode, selection.anchorOffset);
        domRange.collapse(true);
    } else {
        domRange.setEnd(selection.anchorNode, selection.anchorOffset);
        domRange.collapse(false);
    }
    const domSelection = selection.anchorNode.ownerDocument.getSelection();
    domSelection.removeAllRanges();
    domSelection.addRange(domRange);
    try {
        domSelection.extend(selection.focusNode, selection.focusOffset);
    } catch (e) {
        // Firefox yells not happy when setting selection on elem with contentEditable=false.
    }
}

/**
 * Inserts the given characters at the given offset of the given node.
 *
 * @param {string} chars
 * @param {Node} node
 * @param {number} offset
 */
export function insertCharsAt(chars, node, offset) {
    if (node.nodeType === Node.TEXT_NODE) {
        const startValue = node.nodeValue;
        if (offset < 0 || offset > startValue.length) {
            throw new Error(`Invalid ${chars} insertion in text node`);
        }
        node.nodeValue = startValue.slice(0, offset) + chars + startValue.slice(offset);
    } else {
        if (offset < 0 || offset > node.childNodes.length) {
            throw new Error(`Invalid ${chars} insertion in non-text node`);
        }
        const textNode = document.createTextNode(chars);
        if (offset < node.childNodes.length) {
            node.insertBefore(textNode, node.childNodes[offset]);
        } else {
            node.appendChild(textNode);
        }
    }
}

/**
 * Return the deepest child of a given container at a given offset, and its
 * adapted offset.
 *
 * @param container
 * @param offset
 */
export function targetDeepest(container, offset) {
    // TODO check at which point the method is necessary, for now it creates
    // a bug where there is not: it causes renderTextualSelection to put "[]"
    // chars inside a <br/>.

    // while (container.hasChildNodes()) {
    //     let childNodes;
    //     if (container instanceof Element && container.shadowRoot) {
    //         childNodes = container.shadowRoot.childNodes;
    //     } else {
    //         childNodes = container.childNodes;
    //     }
    //     if (offset >= childNodes.length) {
    //         container = container.lastChild;
    //         // The new container might be a text node, so considering only
    //         // the `childNodes` property would be wrong.
    //         offset = nodeLength(container);
    //     } else {
    //         container = childNodes[offset];
    //         offset = 0;
    //     }
    // }
    return [container, offset];
}

export function nodeLength(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        return node.nodeValue.length;
    } else if (node instanceof Element && node.shadowRoot) {
        return node.shadowRoot.childNodes.length;
    } else {
        return node.childNodes.length;
    }
}

/**
 * Insert in the DOM:
 * - `SELECTION_ANCHOR_CHAR` in place for the selection start
 * - `SELECTION_FOCUS_CHAR` in place for the selection end
 *
 * This is used in the function `testEditor`.
 */
export function renderTextualSelection() {
    const selection = document.getSelection();
    if (selection.rangeCount === 0) {
        return;
    }

    const anchor = targetDeepest(selection.anchorNode, selection.anchorOffset);
    const focus = targetDeepest(selection.focusNode, selection.focusOffset);

    // If the range characters have to be inserted within the same parent and
    // the anchor range character has to be before the focus range character,
    // the focus offset needs to be adapted to account for the first insertion.
    const [anchorNode, anchorOffset] = anchor;
    const [focusNode, baseFocusOffset] = focus;
    let focusOffset = baseFocusOffset;
    if (anchorNode === focusNode && anchorOffset <= focusOffset) {
        focusOffset++;
    }
    insertCharsAt('[', ...anchor);
    insertCharsAt(']', focusNode, focusOffset);
}

/**
 * Return a more readable test error messages
 */
export function customErrorMessage(assertLocation, value, expected) {
    const zws = '//zws//';
    value = value.replace('\u200B', zws);
    expected = expected.replace('\u200B', zws);

    return `[${assertLocation}}]\nactual  : '${value}'\nexpected: '${expected}'\n\nStackTrace `;
}

export async function testEditor(Editor = OdooEditor, spec) {
    const testNode = document.createElement('div');
    document.querySelector('#editor-test-container').innerHTML = '';
    document.querySelector('#editor-test-container').appendChild(testNode);

    // Add the content to edit and remove the "[]" markers *before* initializing
    // the editor as otherwise those would genererate mutations the editor would
    // consider and the tests would make no sense.
    testNode.innerHTML = spec.contentBefore;
    const selection = parseTextualSelection(testNode);

    const editor = new Editor(testNode, { toSanitize: false });
    editor.keyboardType = 'PHYSICAL';
    editor.testMode = true;
    if (selection) {
        setTestSelection(selection);
        editor._recordHistorySelection();
    } else {
        document.getSelection().removeAllRanges();
    }

    // we have to sanitize after having put the cursor
    sanitize(editor.editable);

    if (spec.contentBeforeEdit) {
        renderTextualSelection();
        const beforeEditValue = testNode.innerHTML;
        window.chai.expect(beforeEditValue).to.be.equal(
            spec.contentBeforeEdit,
            customErrorMessage('contentBeforeEdit', beforeEditValue, spec.contentBeforeEdit));
        const selection = parseTextualSelection(testNode);
        if (selection) {
            setTestSelection(selection);
        }
    }

    let firefoxExecCommandError = false;
    if (spec.stepFunction) {
        try {
            await spec.stepFunction(editor);
        } catch (err) {
            if (typeof err === 'object' && err.name === 'NS_ERROR_FAILURE') {
                firefoxExecCommandError = true;
            } else {
                throw err;
            }
        }
    }

    if (spec.contentAfterEdit && !firefoxExecCommandError) {
        renderTextualSelection();
        const afterEditValue = testNode.innerHTML;
        window.chai.expect(afterEditValue).to.be.equal(
            spec.contentAfterEdit,
            customErrorMessage('contentAfterEdit', afterEditValue, spec.contentAfterEdit));
        const selection = parseTextualSelection(testNode);
        if (selection) {
            setTestSelection(selection);
        }
    }

    await editor.clean();
    // Same as above: disconnect mutation observers and other things, otherwise
    // reading the "[]" markers would broke the test.
    await editor.destroy();

    if (spec.contentAfter && !firefoxExecCommandError) {
        renderTextualSelection();
        const value = testNode.innerHTML;
        window.chai.expect(value).to.be.equal(
            spec.contentAfter,
            customErrorMessage('contentAfter', value, spec.contentAfter));
    }
    await testNode.remove();

    if (firefoxExecCommandError) {
        // FIXME
        throw new Error('Firefox was not able to test this case because of an execCommand error');
    }
}

/**
 * Unformat the given html in order to use it with `innerHTML`.
 */
export function unformat(html) {
    return html
        .replace(/(^|[^ ])[\s\n]+([^<>]*?)</g, '$1$2<')
        .replace(/>([^<>]*?)[\s\n]+([^ ]|$)/g, '>$1$2');
}

/**
 * await the next tick (as settimeout 0)
 *
 */
export async function nextTick() {
    await new Promise(resolve => {
        setTimeout(resolve);
    });
}

/**
 * await the next tick (as settimeout 0) after the next redrawing frame
 *
 */
export async function nextTickFrame() {
    await new Promise(resolve => {
        window.requestAnimationFrame(resolve);
    });
    await nextTick();
}

/**
 * simple simulation of a click on an element
 *
 * @param el
 * @param options
 */
export async function click(el, options) {
    el.scrollIntoView();
    await nextTickFrame();
    const pos = el.getBoundingClientRect();
    options = Object.assign(
        {
            bubbles: true,
            clientX: pos.left + 1,
            clientY: pos.top + 1,
        },
        options,
    );
    el.dispatchEvent(new MouseEvent('mousedown', options));
    await nextTickFrame();
    el.dispatchEvent(new MouseEvent('mouseup', options));
    await nextTick();
    el.dispatchEvent(new MouseEvent('click', options));
    await nextTickFrame();
}

export async function deleteForward(editor) {
    editor.execCommand('oDeleteForward');
}

export async function deleteBackward(editor) {
    editor.execCommand('oDeleteBackward');
}

export async function insertParagraphBreak(editor) {
    editor.execCommand('oEnter');
}

export async function insertLineBreak(editor) {
    editor.execCommand('oShiftEnter');
}

export async function indentList(editor) {
    editor.execCommand('indentList');
}

export async function outdentList(editor) {
    editor.execCommand('indentList', 'outdent');
}

export async function toggleOrderedList(editor) {
    editor.execCommand('toggleList', 'OL');
}

export async function toggleUnorderedList(editor) {
    editor.execCommand('toggleList', 'UL');
}

export async function toggleCheckList(editor) {
    editor.execCommand('toggleList', 'CL');
}

export async function toggleBold() {
    document.execCommand('bold');
    // Wait for the timeout in the MutationObserver to happen.
    return new Promise(resolve => setTimeout(() => resolve(), 200));
}

export async function createLink(editor, content) {
    editor.execCommand('createLink', '#', content);
}

export async function insertText(editor, text) {
    // We create and dispatch an event to mock the insert Text.
    // Unfortunatly those Event are flagged `isTrusted: false`.
    // So we have no choice and need to detect them inside the Editor.
    // But it's the closest to real Browser we can go.
    var event = new InputEvent('input', {
        inputType: 'insertText',
        data: text,
        bubbles: true,
        cancelable: true,
    });
    editor.editable.dispatchEvent(event);
}

export function undo(editor) {
    editor.historyUndo();
}

export function redo(editor) {
    editor.historyRedo();
}

export class BasicEditor extends OdooEditor {}
