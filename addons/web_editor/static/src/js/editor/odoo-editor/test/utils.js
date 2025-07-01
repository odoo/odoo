/** @odoo-module **/

import { OdooEditor } from '../src/OdooEditor.js';
import { sanitize } from '../src/utils/sanitize.js';
import {
    closestElement,
    makeZeroWidthCharactersVisible,
    insertSelectionChars,
} from '../src/utils/utils.js';

export const Direction = {
    BACKWARD: 'BACKWARD',
    FORWARD: 'FORWARD',
};

// True iff test is being run with its mobile implementation.
let isMobileTest = false;
// True iff test has mobile implementation for any called method.
let hasMobileTest = false;

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
export async function setTestSelection(selection, doc = document) {
    const domRange = doc.createRange();
    if (selection.direction === Direction.FORWARD) {
        domRange.setStart(selection.anchorNode, selection.anchorOffset);
        domRange.collapse(true);
    } else {
        domRange.setEnd(selection.anchorNode, selection.anchorOffset);
        domRange.collapse(false);
    }
    const domSelection = doc.getSelection();
    domSelection.removeAllRanges();
    domSelection.addRange(domRange);
    try {
        domSelection.extend(selection.focusNode, selection.focusOffset);
    } catch {
        // Firefox throws NS_ERROR_FAILURE when setting selection on element
        // with contentEditable=false for no valid reason since non-editable
        // content are selectable by the user anyway.
    }
    await nextTick(); // Wait a tick for selectionchange events.
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
export function renderTextualSelection(editor) {
    const selection = editor.document.getSelection();
    if (selection.rangeCount === 0) {
        return;
    }
    editor.observerUnactive('renderTextualSelection');
    insertSelectionChars(selection.anchorNode, selection.anchorOffset, selection.focusNode, selection.focusOffset);
    editor.observerActive('renderTextualSelection');
}

/**
 * Return a more readable test error messages
 */
export function customErrorMessage(assertLocation, value, expected) {
    const tab = '//TAB//';
    value = makeZeroWidthCharactersVisible(value).replaceAll('\u0009', tab);
    expected = makeZeroWidthCharactersVisible(expected).replaceAll('\u0009', tab);

    return `${(isMobileTest ? '[MOBILE VERSION: ' : '[')}${assertLocation}]\nactual  : '${value}'\nexpected: '${expected}'\n\nStackTrace `;
}

/**
 * Return whether the device is in mobile view or not
 */
export function _isMobile(){
    return matchMedia('(max-width: 767px)').matches;
}

/**
 * Remove all check-ids from the test container (checklists, stars)
 *
 * @param {Element} testContainer
 */
function removeCheckIds(testContainer) {
    for (const li of testContainer.querySelectorAll('li[id^="checkId-"]')) {
        li.removeAttribute('id');
    }
}

export async function testEditor(Editor = OdooEditor, spec, options = {}) {
    hasMobileTest = false;
    isMobileTest = options.isMobile;

    const testNode = document.createElement('div');
    const testContainer = document.querySelector('#editor-test-container');
    testContainer.innerHTML = '';
    testContainer.append(testNode);
    testContainer.append(document.createTextNode('')); // Formatting spaces.
    let styleTag;
    if (spec.styleContent) {
        styleTag = document.createElement('style');
        styleTag.textContent = spec.styleContent;
        testContainer.append(styleTag);
    }

    // Add the content to edit and remove the "[]" markers *before* initializing
    // the editor as otherwise those would genererate mutations the editor would
    // consider and the tests would make no sense.
    testNode.innerHTML = spec.contentBefore;
    // Setting a selection in the DOM before initializing the editor to ensure
    // every test is run with the same preconditions.
    await setTestSelection({
        anchorNode: testNode.parentElement, anchorOffset: 0,
        focusNode: testNode.parentElement, focusOffset: 0,
    });
    const selection = parseTextualSelection(testNode);

    // We disable the `toSanitize` option so we set the test selection on the
    // raw, unsanitized HTML. We'll sanitize after having set the selection.
    const editor = new Editor(testNode, Object.assign({ toSanitize: false }, options));
    let error = false;
    try {
        editor.keyboardType = 'PHYSICAL';
        editor.testMode = true;
        if (selection) {
            await setTestSelection(selection);
        } else {
            document.getSelection().removeAllRanges();
        }

        // Now the selection is set we can finally sanitize.
        sanitize(editor.editable);

        // In normal circumstances the editor sanitizes its content in its
        // constructor, before initializing the history. For the purposes of
        // setting the test's selection, we only sanitize now, which means the
        // changes made by `sanitize` are included in a step (which could well
        // be rolled back if what the step function does triggers it), and the
        // sanitization can be undone. This is not how the editor normally
        // behaves. To make it closer to reality, we now reset the history.
        editor.historyReset();
        editor.historyStep();

        if (selection) {
            editor._recordHistorySelection();
        }

        if (spec.contentBeforeEdit) {
            if (spec.removeCheckIds) {
                removeCheckIds(testContainer);
            }
            renderTextualSelection(editor);
            const beforeEditValue = testNode.innerHTML;
            window.chai.expect(beforeEditValue).to.be.equal(
                spec.contentBeforeEdit,
                customErrorMessage('contentBeforeEdit', beforeEditValue, spec.contentBeforeEdit));
            const selection = parseTextualSelection(testNode);
            if (selection) {
                await setTestSelection(selection);
            }
        }

        // Wait for selectionchange handlers to react before any actual testing.
        await Promise.resolve();

        if (spec.stepFunction) {
            try {
                await spec.stepFunction(editor);
            } catch (e) {
                e.message = (isMobileTest ? '[MOBILE VERSION] ' : '') + e.message;
                throw e;
            }
        }

        if (spec.contentAfterEdit) {
            renderTextualSelection(editor);
            if (spec.removeCheckIds) {
                removeCheckIds(testContainer);
            }
            const afterEditValue = testNode.innerHTML;
            window.chai.expect(afterEditValue).to.be.equal(
                spec.contentAfterEdit,
                customErrorMessage('contentAfterEdit', afterEditValue, spec.contentAfterEdit));
            const selection = parseTextualSelection(testNode);
            if (selection) {
                await setTestSelection(selection);
            }
        }
    } catch (err) {
        error = err;
    }

    await editor.clean();
    // Same as above: disconnect mutation observers and other things, otherwise
    // reading the "[]" markers would broke the test.
    await editor.destroy();

    if (!error) {
        try {
            if (spec.contentAfter) {
                renderTextualSelection(editor);
                if (spec.removeCheckIds) {
                    removeCheckIds(testContainer);
                }
                const value = testNode.innerHTML;
                window.chai.expect(value).to.be.equal(
                    spec.contentAfter,
                    customErrorMessage('contentAfter', value, spec.contentAfter));
            }
        } catch (err) {
            error = err;
        }
    }

    await testNode.remove();

    if (error) {
        throw error;
    } else if (hasMobileTest && !isMobileTest) {
        const li = document.createElement('li');
        li.classList.add('test', 'pass', 'pending');
        const h2 = document.createElement('h2');
        h2.textContent = 'FIXME: [Mobile Test] skipped';
        li.append(h2);
        const mochaSuite = [...document.querySelectorAll('#mocha-report li.suite > ul')].pop();
        if (mochaSuite) {
            mochaSuite.append(li);
        }
        // Mobile tests are temporarily disabled because they are not
        // representative of reality. They will be re-enabled when the mobile
        // editor will be ready.
        // await testEditor(Editor, spec, { ...options, isMobile: true });
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
            clientX: pos.left + 1,
            clientY: pos.top + 1,
        },
        options,
    );
    triggerEvent(el, 'mousedown', options);
    await nextTickFrame();
    triggerEvent(el, 'mouseup', options);
    await nextTick();
    triggerEvent(el, 'click', options);
    await nextTickFrame();
}

export async function deleteForward(editor) {
    const selection = document.getSelection();
    if (selection.isCollapsed) {
        editor.execCommand('oDeleteForward');
    } else {
        // Better representation of what happened in the editor when the user
        // presses the delete key.
        await triggerEvent(editor.editable, 'keydown', { key: 'Delete' });
        editor.document.execCommand('delete');
    }
}

export async function deleteBackward(editor) {
    // This method has two implementations (desktop and mobile).
    if (isMobileTest) {
        // Some mobile keyboard use input event to trigger delete.
        // This is a way to simulate this behavior.
        const inputEvent = new InputEvent('input', {
            inputType: 'deleteContentBackward',
            data: null,
            bubbles: true,
            cancelable: false,
        });
        editor._onInput(inputEvent);
    } else {
        hasMobileTest = true; // Flag test for a re-run as mobile.
        const selection = document.getSelection();
        if (selection.isCollapsed) {
            editor.execCommand('oDeleteBackward');
        } else {
            // Better representation of what happened in the editor when the user
            // presses the backspace key.
            await triggerEvent(editor.editable, 'keydown', { key: 'Backspace' });
            editor.document.execCommand('delete');
        }
    }
}

export async function insertParagraphBreak(editor) {
    editor.execCommand('oEnter');
}

export async function switchDirection(editor) {
    editor.execCommand('switchDirection');
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

export async function insertText(editor, text) {
    // Create and dispatch events to mock text insertion. Unfortunatly, the
    // events will be flagged `isTrusted: false` by the browser, requiring
    // the editor to detect them since they would not trigger the default
    // browser behavior otherwise.
    for (const char of text) {
        // KeyDownEvent is required to trigger deleteRange.
        triggerEvent(editor.editable, 'keydown', { key: char });
        // KeyPressEvent is not required but is triggered like in the browser.
        triggerEvent(editor.editable, 'keypress', { key: char });
        // InputEvent is required to simulate the insert text.
        triggerEvent(editor.editable, 'input', {
            inputType: 'insertText',
            data: char,
        });
        // KeyUpEvent is not required but is triggered like the browser would.
        triggerEvent(editor.editable, 'keyup', { key: char });
    }
}

export function undo(editor) {
    editor.historyUndo();
}

export function redo(editor) {
    editor.historyRedo();
}

/**
 * The class exists because the original `InputEvent` does not allow to override
 * its inputType property.
 */
class SimulatedInputEvent extends InputEvent {
    constructor(type, eventInitDict) {
        super(type, eventInitDict);
        this.eventInitDict = eventInitDict;
    }
    get inputType() {
        return this.eventInitDict.inputType;
    }
}
function getEventConstructor(win, type) {
    const eventTypes = {
        'pointer': win.MouseEvent,
        'contextmenu': win.MouseEvent,
        'select': win.MouseEvent,
        'wheel': win.MouseEvent,
        'click': win.MouseEvent,
        'dblclick': win.MouseEvent,
        'mousedown': win.MouseEvent,
        'mouseenter': win.MouseEvent,
        'mouseleave': win.MouseEvent,
        'mousemove': win.MouseEvent,
        'mouseout': win.MouseEvent,
        'mouseover': win.MouseEvent,
        'mouseup': win.MouseEvent,
        'compositionstart': win.CompositionEvent,
        'compositionend': win.CompositionEvent,
        'compositionupdate': win.CompositionEvent,
        'input': SimulatedInputEvent,
        'beforeinput': SimulatedInputEvent,
        'keydown': win.KeyboardEvent,
        'keypress': win.KeyboardEvent,
        'keyup': win.KeyboardEvent,
        'dragstart': win.DragEvent,
        'dragend': win.DragEvent,
        'drop': win.DragEvent,
        'beforecut': win.ClipboardEvent,
        'copy': win.ClipboardEvent,
        'cut': win.ClipboardEvent,
        'paste': win.ClipboardEvent,
        'touchstart': win.TouchEvent,
        'touchend': win.TouchEvent,
        'selectionchange': win.Event,
    };
    if (!eventTypes[type]) {
        throw new Error('The event "' + type + '" is not implemented for the tests.');
    }
    return eventTypes[type];
}

export async function triggerEvent(
    el,
    eventName,
    options,
) {
    const currentElement = closestElement(el);
    options = Object.assign(
        {
            view: el.ownerDocument.defaultView,
            bubbles: true,
            composed: true,
            cancelable: true,
            isTrusted: true,
        },
        options,
    );
    const EventClass = getEventConstructor(el.ownerDocument.defaultView, eventName);
    if (EventClass.name === 'ClipboardEvent' && !('clipboardData' in options)) {
        throw new Error('ClipboardEvent must have clipboardData in options');
    }
    const ev = new EventClass(eventName, options);

    currentElement.dispatchEvent(ev);
    await nextTick();
    return ev;
}

// Mock an paste event and send it to the editor.
async function pasteData (editor, text, type) {
    var mockEvent = {
        dataType: 'text/plain',
        data: text,
        clipboardData: {
            getData: (datatype) => type === datatype ? text : null,
            files: [],
            items: [],
        },
        preventDefault: () => { },
    };
    await editor._onPaste(mockEvent);
};

export const pasteText = async (editor, text) => pasteData(editor, text, 'text/plain');
export const pasteHtml = async (editor, html) => pasteData(editor, html, 'text/html');
export const pasteOdooEditorHtml = async (editor, html) => pasteData(editor, html, 'text/odoo-editor');
const overridenDomClass = [
    'HTMLBRElement',
    'HTMLHeadingElement',
    'HTMLParagraphElement',
    'HTMLPreElement',
    'HTMLQuoteElement',
    'HTMLTableCellElement',
    'Text',
];

export function patchEditorIframe(iframe) {
    const iframeWindow = iframe.contentWindow;

    for (const overridenClass of overridenDomClass) {
        const windowClassPrototype = window[overridenClass].prototype;
        const iframeWindowClassPrototype = iframeWindow[overridenClass].prototype;
        const iframePrototypeMethodNames = Object.keys(iframeWindowClassPrototype);

        for (const methodName of Object.keys(windowClassPrototype)) {
            if (!iframePrototypeMethodNames.includes(methodName)) {
                iframeWindowClassPrototype[methodName] = windowClassPrototype[methodName];
            }
        }
    }
}

export class BasicEditor extends OdooEditor {}
