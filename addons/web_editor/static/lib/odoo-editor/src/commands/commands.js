/** @odoo-module **/
import {
    ancestors,
    descendants,
    childNodeIndex,
    closestBlock,
    closestElement,
    closestPath,
    DIRECTIONS,
    findNode,
    getCursorDirection,
    getCursors,
    getDeepRange,
    getInSelection,
    getListMode,
    getNormalizedCursorPosition,
    getSelectedNodes,
    getTraversedNodes,
    insertAndSelectZws,
    insertText,
    isBlock,
    isFormat,
    isSelectionFormat,
    isColorGradient,
    isContentTextNode,
    isShrunkBlock,
    isVisible,
    isVisibleStr,
    leftLeafFirstPath,
    preserveCursor,
    rightPos,
    setSelection,
    setCursorStart,
    setTagName,
    splitAroundUntil,
    splitElement,
    splitTextNode,
    startPos,
    nodeSize,
    allowsParagraphRelatedElements,
    isUnbreakable,
    makeContentsInline,
} from '../utils/utils.js';

const TEXT_CLASSES_REGEX = /\btext-[^\s]*\b/g;
const BG_CLASSES_REGEX = /\bbg-[^\s]*\b/g;

function insert(editor, data, isText = true) {
    if (!data) {
        return;
    }
    const selection = editor.document.getSelection();
    const range = selection.getRangeAt(0);
    let startNode;
    let insertBefore = false;
    if (selection.isCollapsed) {
        if (range.startContainer.nodeType === Node.TEXT_NODE) {
            insertBefore = !range.startOffset;
            splitTextNode(range.startContainer, range.startOffset, DIRECTIONS.LEFT);
            startNode = range.startContainer;
        }
    } else {
        editor.deleteRange(selection);
    }

    const fakeEl = document.createElement('fake-element');
    const fakeElFirstChild = document.createElement('fake-element-fc');
    const fakeElLastChild = document.createElement('fake-element-lc');
    if (isText) {
        fakeEl.innerText = data;
    } else {
        fakeEl.innerHTML = data;
    }

    // In case the html inserted starts with a list and will be inserted within
    // a list, unwrap the list elements from the list.
    if (closestElement(selection.anchorNode, 'UL, OL') &&
        (fakeEl.firstChild.nodeName === 'UL' || fakeEl.firstChild.nodeName === 'OL')) {
       fakeEl.replaceChildren(...fakeEl.firstChild.childNodes);
    }

    // In case the html inserted is all contained in a single root <p> or <li>
    // tag, we take the all content of the <p> or <li> and avoid inserting the
    // <p> or <li>.
    if (fakeEl.childElementCount === 1 && (fakeEl.firstChild.nodeName === 'P' || fakeEl.firstChild.nodeName === 'LI')) {
        const p = fakeEl.firstElementChild;
        fakeEl.replaceChildren(...p.childNodes);
    } else if (fakeEl.childElementCount > 1) {
        // Grab the content of the first child block and isolate it.
        if (isBlock(fakeEl.firstChild)) {
            fakeElFirstChild.replaceChildren(...fakeEl.firstElementChild.childNodes);
            fakeEl.firstElementChild.remove();
        }
        // Grab the content of the last child block and isolate it.
        if (isBlock(fakeEl.lastChild)) {
            fakeElLastChild.replaceChildren(...fakeEl.lastElementChild.childNodes);
            fakeEl.lastElementChild.remove();
        }
    }

    startNode = startNode || editor.document.getSelection().anchorNode;
    if (startNode.nodeType === Node.ELEMENT_NODE) {
        if (selection.anchorOffset === 0) {
            const textNode = editor.document.createTextNode('');
            startNode.prepend(textNode);
            startNode = textNode;
        } else {
            startNode = startNode.childNodes[selection.anchorOffset - 1];
        }
    }

    // If we have isolated block content, first we split the current focus
    // element if it's a block then we insert the content in the right places.
    let currentNode = startNode;
    let lastChildNode = false;
    const _insertAt = (reference, nodes, insertBefore) => {
        for (const child of (insertBefore ? nodes.reverse() : nodes)) {
            reference[insertBefore ? 'before' : 'after'](child);
            reference = child;
        }
    }
    if (fakeElLastChild.hasChildNodes()) {
        const toInsert = [...fakeElLastChild.childNodes]; // Prevent mutation
        _insertAt(currentNode, [...toInsert], insertBefore);
        currentNode = insertBefore ? toInsert[0] : currentNode;
        lastChildNode = toInsert[toInsert.length - 1];
    }
    if (fakeElFirstChild.hasChildNodes()) {
        const toInsert = [...fakeElFirstChild.childNodes]; // Prevent mutation
        _insertAt(currentNode, [...toInsert], insertBefore);
        currentNode = toInsert[toInsert.length - 1];
        insertBefore = false;
    }

    // If all the Html have been isolated, We force a split of the parent element
    // to have the need new line in the final result
    if (!fakeEl.hasChildNodes()) {
        if (isUnbreakable(closestBlock(currentNode.nextSibling))) {
            currentNode.nextSibling.oShiftEnter(0);
        } else {
            // If we arrive here, the o_enter index should always be 0.
            const parent = currentNode.nextSibling.parentElement;
            const index = [...parent.childNodes].indexOf(currentNode.nextSibling);
            currentNode.nextSibling.parentElement.oEnter(index);
        }
    }

    let nodeToInsert;
    const insertedNodes = [...fakeEl.childNodes];
    while ((nodeToInsert = fakeEl.childNodes[0])) {
        if (isBlock(nodeToInsert) && !allowsParagraphRelatedElements(currentNode)) {
            // Split blocks at the edges if inserting new blocks (preventing
            // <p><p>text</p></p> or <li><li>text</li></li> scenarios).
            while (
                currentNode.parentElement !== editor.editable &&
                (!allowsParagraphRelatedElements(currentNode.parentElement) ||
                currentNode.parentElement.nodeName === 'LI')
            ) {
                if (isUnbreakable(currentNode.parentElement)) {
                    makeContentsInline(fakeEl);
                    nodeToInsert = fakeEl.childNodes[0];
                    break;
                }
                let offset = childNodeIndex(currentNode);
                if (!insertBefore) {
                    offset += 1;
                }
                if (offset) {
                    const [left, right] = splitElement(currentNode.parentElement, offset);
                    currentNode = insertBefore ? right : left;
                } else {
                    currentNode = currentNode.parentElement;
                }
            }
        }
        if (insertBefore) {
            currentNode.before(nodeToInsert);
            insertBefore = false;
        } else {
            currentNode.after(nodeToInsert);
        }
        if (currentNode.tagName !== 'BR' && isShrunkBlock(currentNode)) {
            currentNode.remove();
        }
        currentNode = nodeToInsert;
    }

    currentNode = lastChildNode || currentNode;
    selection.removeAllRanges();
    const newRange = new Range();
    const lastPosition = rightPos(currentNode);
    newRange.setStart(lastPosition[0], lastPosition[1]);
    newRange.setEnd(lastPosition[0], lastPosition[1]);
    selection.addRange(newRange);
    return insertedNodes;
}
function align(editor, mode) {
    const sel = editor.document.getSelection();
    const visitedBlocks = new Set();
    const traversedNode = getTraversedNodes(editor.editable);
    for (const node of traversedNode) {
        if (isContentTextNode(node) && isVisible(node)) {
            const block = closestBlock(node);
            if (!visitedBlocks.has(block)) {
                const hasModifier = getComputedStyle(block).textAlign === mode;
                if (!hasModifier && block.isContentEditable) {
                    block.oAlign(sel.anchorOffset, mode);
                }
                visitedBlocks.add(block);
            }
        }
    }
}

/**
 * Applies a css or class color (fore- or background-) to an element.
 * Replace the color that was already there if any.
 *
 * @param {Element} element
 * @param {string} color hexadecimal or bg-name/text-name class
 * @param {string} mode 'color' or 'backgroundColor'
 */
function colorElement(element, color, mode) {
    const newClassName = element.className
        .replace(mode === 'color' ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX, '')
        .replace(/\btext-gradient\b/g, '') // cannot be combined with setting a background
        .replace(/\s+/, ' ');
    element.className !== newClassName && (element.className = newClassName);
    element.style['background-image'] = '';
    if (mode === 'backgroundColor') {
        element.style['background'] = '';
    }
    if (color.startsWith('text') || color.startsWith('bg-')) {
        element.style[mode] = '';
        element.classList.add(color);
    } else if (isColorGradient(color)) {
        element.style[mode] = '';
        if (mode === 'color') {
            element.style['background'] = '';
            element.style['background-image'] = color;
            element.classList.add('text-gradient');
        } else {
            element.style['background-image'] = color;
        }
    } else {
        element.style[mode] = color;
    }
}

/**
 * Returns true if the given element has a visible color (fore- or
 * -background depending on the given mode).
 *
 * @param {Element} element
 * @param {string} mode 'color' or 'backgroundColor'
 * @returns {boolean}
 */
function hasColor(element, mode) {
    const style = element.style;
    const parent = element.parentNode;
    const classRegex = mode === 'color' ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX;
    if (isColorGradient(style['background-image'])) {
        if (element.classList.contains('text-gradient')) {
            if (mode === 'color') {
                return true;
            }
        } else {
            if (mode !== 'color') {
                return true;
            }
        }
    }
    return (
        (style[mode] && style[mode] !== 'inherit' && style[mode] !== parent.style[mode]) ||
        (classRegex.test(element.className) &&
            getComputedStyle(element)[mode] !== getComputedStyle(parent)[mode])
    );
}
/**
 * This function abstracts the difficulty of applying a inline style to a
 * selection. TODO: This implementations potentially adds one span per text
 * node, in an ideal world it would wrap all concerned nodes in one span
 * whenever possible.
 * @param {Element => void} applyStyle Callback that receives an element to
 * which the wanted style should be applied
 * @param {string | [string, string]} [style] the format type to toggle or an
 * array with the style property name and the value to apply to it
 * @param {boolean} [shouldApply=true] set to false to undo a style rather than
 * apply it.
 * @returns {Element[]} the elements on which the style was changed.
 */
export function applyInlineStyle(editor, applyStyle, style, shouldApply=true) {
    getDeepRange(editor.editable, { splitText: true, select: true });
    const sel = editor.document.getSelection();
    const { startContainer, startOffset, endContainer, endOffset } = sel.getRangeAt(0);
    const { anchorNode, anchorOffset, focusNode, focusOffset } = sel;
    const direction = getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset);
    const [
        normalizedStartContainer,
        normalizedStartOffset
    ] = getNormalizedCursorPosition(startContainer, startOffset);
    const [
        normalizedEndContainer,
        normalizedEndOffset
    ] = getNormalizedCursorPosition(endContainer, endOffset);
    const selectedTextNodes = getSelectedNodes(editor.editable).filter(node => {
        const atLeastOneCharFromNodeInSelection = !(
            (node === normalizedEndContainer && normalizedEndOffset === 0) ||
            (node === normalizedStartContainer && normalizedStartOffset === node.textContent.length)
        );
        return isContentTextNode(node) && atLeastOneCharFromNodeInSelection;
    });
    const textNodesToFormat = selectedTextNodes.filter(node => {
        let isApplied;
        if (Array.isArray(style) && style[style[0]]) {
            let ancestor = node;
            while (ancestor) {
                if (ancestor.style[style[0]]) {
                    isApplied = ancestor.style[style[0]] === style[1];
                    break;
                } else {
                    ancestor = ancestor.parentElement;
                }
            }
        } else {
            isApplied = isFormat[style] && isFormat[style](node);
        }
        return shouldApply ? !isApplied : isApplied;
    });
    const changedElements = [];
    for (const textNode of textNodesToFormat) {
        // If text node ends after the end of the selection, split it and
        // keep the part that is inside.
        if (endContainer === textNode && endOffset < textNode.textContent.length) {
            // No reassignement needed, entirely dependent on the
            // splitTextNode implementation.
            splitTextNode(textNode, endOffset, DIRECTIONS.LEFT);
        }
        // If text node starts before the beginning of the selection, split it
        // and keep the part that is inside as textNode.
        if (startContainer === textNode && startOffset > 0) {
            // No reassignement needed, entirely dependent on the
            // splitTextNode implementation.
            splitTextNode(textNode, startOffset, DIRECTIONS.RIGHT);
        }
        // If the parent is not inline or is not completely in the
        // selection, wrap text node in inline node. Also skips <a> tags to
        // work with native `removeFormat` command
        const siblings = [...textNode.parentElement.childNodes];
        if (
            isBlock(textNode.parentElement) ||
            !(
                selectedTextNodes.includes(siblings[0]) &&
                selectedTextNodes.includes(siblings[siblings.length - 1])
            ) ||
            textNode.parentElement.tagName === 'A'
        ) {
            const newParent = document.createElement('span');
            textNode.after(newParent);
            newParent.appendChild(textNode);
        }
        applyStyle(textNode.parentElement);
        changedElements.push(textNode.parentElement);
    }
    if (selectedTextNodes[0] && selectedTextNodes[0].textContent === '\u200B') {
        setSelection(selectedTextNodes[0], 0);
    } else if (selectedTextNodes.length) {
        const firstNode = selectedTextNodes[0];
        const lastNode = selectedTextNodes[selectedTextNodes.length - 1];
        if (direction === DIRECTIONS.RIGHT) {
            setSelection(firstNode, 0, lastNode, lastNode.length);
        } else {
            setSelection(lastNode, lastNode.length, firstNode, 0);
        }
    }
    return changedElements;
}
const styles = {
    bold: {
        is: editable => isSelectionFormat(editable, 'bold'),
        name: 'fontWeight',
        value: 'bolder',
    },
    italic: {
        is: editable => isSelectionFormat(editable, 'italic'),
        name: 'fontStyle',
        value: 'italic',
    },
    underline: {
        is: editable => isSelectionFormat(editable, 'underline'),
        name: 'textDecorationLine',
        value: 'underline',
    },
    strikeThrough: {
        is: editable => isSelectionFormat(editable, 'strikeThrough'),
        name: 'textDecorationLine',
        value: 'line-through',
    },
    switchDirection: {
        is: editable => isSelectionFormat(editable, 'switchDirection'),
    },
};

export function toggleFormat(editor, format) {
    const selection = editor.document.getSelection();
    if (!selection.rangeCount) return;
    const wasCollapsed = selection.getRangeAt(0).collapsed;
    let zws;
    if (wasCollapsed) {
        if (selection.anchorNode.nodeType === Node.TEXT_NODE && selection.anchorNode.textContent === '\u200b') {
            zws = selection.anchorNode;
            selection.getRangeAt(0).selectNode(zws);
        } else {
            zws = insertAndSelectZws(selection);
        }
    }
    getDeepRange(editor.editable, { splitText: true, select: true, correctTripleClick: true });
    const {anchorNode, anchorOffset, focusNode, focusOffset} = editor.document.getSelection();
    const style = styles[format];
    const selectedTextNodes = getSelectedNodes(editor.editable)
        .filter(n => n.nodeType === Node.TEXT_NODE && n.nodeValue.length);
    const isAlreadyFormatted = style.is(editor.editable);
    let changedElements = [];
    if (isAlreadyFormatted && style.name === 'textDecorationLine') {
        for (const textNode of selectedTextNodes) {
            const closestDecorated = closestElement(textNode, `[style*="text-decoration-line: ${style.value}"]`);
            if (closestDecorated) {
                const splitResult = splitAroundUntil(textNode, closestDecorated);
                const decorationToRemove = splitResult[0] || splitResult[1] || closestDecorated;
                decorationToRemove.style.removeProperty('text-decoration-line');
                if (!decorationToRemove.style.cssText) {
                    for (const child of decorationToRemove.childNodes) {
                        decorationToRemove.before(child);
                        changedElements.push(child);
                    }
                    decorationToRemove.remove();
                }
            }
        }
        if (wasCollapsed) {
            const siblings = [...zws.parentElement.childNodes];
            if (
                selectedTextNodes.includes(siblings[0]) &&
                selectedTextNodes.includes(siblings[siblings.length - 1])
            ) {
                zws.parentElement.setAttribute('oe-zws-empty-inline', '');
            } else {
                const span = document.createElement('span');
                span.setAttribute('oe-zws-empty-inline', '');
                zws.before(span);
                span.append(zws);

            }
            setSelection(zws, 1);
        } else {
            setSelection(anchorNode, anchorOffset, focusNode, focusOffset);
        }
    } else if (format === 'switchDirection') {
        const defaultDirection = editor.options.direction;
        for (const block of new Set(selectedTextNodes.map(textNode => closestBlock(textNode)))) {
            if (isAlreadyFormatted) {
                block.removeAttribute('dir');
            } else {
                block.setAttribute('dir', defaultDirection === 'ltr' ? 'rtl' : 'ltr');
            }
            changedElements.push(block);
        }
    } else {
        changedElements = applyInlineStyle(editor, el => {
            if (isAlreadyFormatted) {
                const block = closestBlock(el);
                el.style[style.name] = style.is(block) ? 'normal' : getComputedStyle(block)[style.name];
            } else if (style.name === 'textDecorationLine' && el.style[style.name]) {
                // The <span> (el) has a text decoration and we want to set
                // another. We don't want to replace the old with the new, we
                // want to add a new one (eg it was underlined, we want it also
                // strikeThrough).
                const newChild = document.createElement('span');
                const children = [...el.childNodes];
                el.prepend(newChild);
                newChild.append(...children);
                newChild.style[style.name] = style.value;
            } else {
                el.style[style.name] = style.value;
            }
            if (zws) {
                const siblings = [...zws.parentElement.childNodes];
                if (
                    selectedTextNodes.includes(siblings[0]) &&
                    selectedTextNodes.includes(siblings[siblings.length - 1])
                ) {
                    zws.parentElement.setAttribute('oe-zws-empty-inline', '');
                } else {
                    const span = document.createElement('span');
                    span.setAttribute('oe-zws-empty-inline', '');
                    zws.before(span);
                    span.append(zws);

                }
            }
        }, format, !isAlreadyFormatted);
    }
    return changedElements;
}
function addColumn(editor, beforeOrAfter) {
    getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding td.
    const c = getInSelection(editor.document, 'td');
    if (!c) return;
    const i = [...closestElement(c, 'tr').querySelectorAll('th, td')].findIndex(td => td === c);
    const column = closestElement(c, 'table').querySelectorAll(`tr td:nth-of-type(${i + 1})`);
    column.forEach(row => row[beforeOrAfter](document.createElement('td')));
}
function addRow(editor, beforeOrAfter) {
    getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding tr.
    const row = getInSelection(editor.document, 'tr');
    if (!row) return;
    const newRow = document.createElement('tr');
    const cells = row.querySelectorAll('td');
    newRow.append(...Array.from(Array(cells.length)).map(() => document.createElement('td')));
    row[beforeOrAfter](newRow);
}
function deleteTable(editor, table) {
    table = table || getInSelection(editor.document, 'table');
    if (!table) return;
    const p = document.createElement('p');
    p.appendChild(document.createElement('br'));
    table.before(p);
    table.remove();
    setSelection(p, 0);
}

// This is a whitelist of the commands that are implemented by the
// editor itself rather than the node prototypes. It might be
// possible to switch the conditions and test if the method exist on
// `sel.anchorNode` rather than relying on an expicit whitelist, but
// the behavior would change if a method name exists both on the
// editor and on the nodes. This is too risky to change in the
// absence of a strong test suite, so the whitelist stays for now.
export const editorCommands = {
    // Insertion
    insertHTML: (editor, data) => {
        return insert(editor, data, false);
    },
    insertText: (editor, data) => {
        return insert(editor, data);
    },
    insertFontAwesome: (editor, faClass = 'fa fa-star') => {
        const insertedNode = editorCommands.insertHTML(editor, '<i></i>')[0];
        insertedNode.className = faClass;
        const position = rightPos(insertedNode);
        setSelection(...position, ...position, false);
    },

    // History
    undo: editor => editor.historyUndo(),
    redo: editor => editor.historyRedo(),

    // Change tags
    setTag(editor, tagName) {
        const restoreCursor = preserveCursor(editor.document);
        const range = getDeepRange(editor.editable, { correctTripleClick: true });
        const selectedBlocks = [...new Set(getTraversedNodes(editor.editable, range).map(closestBlock))];
        for (const block of selectedBlocks) {
            if (
                ['P', 'PRE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BLOCKQUOTE'].includes(
                    block.nodeName,
                )
            ) {
                setSelection(block, 0, block, nodeSize(block));
                editor.historyPauseSteps();
                editor.execCommand('removeFormat');
                editor.historyUnpauseSteps();
                setTagName(block, tagName);
            } else {
                // eg do not change a <div> into a h1: insert the h1
                // into it instead.
                const newBlock = editor.document.createElement(tagName);
                const children = [...block.childNodes];
                block.insertBefore(newBlock, block.firstChild);
                children.forEach(child => newBlock.appendChild(child));
            }
        }
        restoreCursor();
        editor.historyStep();
    },

    // Formats
    // -------------------------------------------------------------------------
    bold: editor => toggleFormat(editor, 'bold'),
    italic: editor => toggleFormat(editor, 'italic'),
    underline: editor => toggleFormat(editor, 'underline'),
    strikeThrough: editor => toggleFormat(editor, 'strikeThrough'),
    switchDirection: editor => {
        const changedElements = toggleFormat(editor, 'switchDirection');
        for (const element of changedElements) {
            const style = getComputedStyle(element);
            if (style.direction === 'ltr' && style.textAlign === 'right') {
                element.style.setProperty('text-align', 'left');
            } else if (style.direction === 'rtl' && style.textAlign === 'left') {
                element.style.setProperty('text-align', 'right');
            }
        }
    },
    removeFormat: editor => {
        editor.document.execCommand('removeFormat');
        for (const node of getTraversedNodes(editor.editable)) {
            // The only possible background image on text is the gradient.
            closestElement(node).style.backgroundImage = '';
        }
    },

    // Align
    justifyLeft: editor => align(editor, 'left'),
    justifyRight: editor => align(editor, 'right'),
    justifyCenter: editor => align(editor, 'center'),
    justifyFull: editor => align(editor, 'justify'),
    /**
     * @param {string} size A valid css size string
     */
    setFontSize: (editor, size) => {
        const selection = editor.document.getSelection();
        if (!selection.rangeCount) return;
        if (selection.getRangeAt(0).collapsed) {
            insertAndSelectZws(selection);
        }
        applyInlineStyle(editor, element => {
            element.style.fontSize = size;
        }, ['fontSize', size]);
    },

    // Link
    createLink: (editor, link, content) => {
        const sel = editor.document.getSelection();
        if (content && !sel.isCollapsed) {
            editor.deleteRange(sel);
        }
        if (sel.isCollapsed) {
            insertText(sel, content || 'link');
        }
        const currentLink = closestElement(sel.focusNode, 'a');
        link = link || prompt('URL or Email', (currentLink && currentLink.href) || 'http://');
        const res = editor.document.execCommand('createLink', false, link);
        if (res) {
            setSelection(sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset);
            const node = findNode(closestPath(sel.focusNode), node => node.tagName === 'A');
            for (const [param, value] of Object.entries(editor.options.defaultLinkAttributes)) {
                node.setAttribute(param, `${value}`);
            }
            const pos = [node.parentElement, childNodeIndex(node) + 1];
            setSelection(...pos, ...pos, false);
        }
    },
    unlink: editor => {
        const sel = editor.document.getSelection();
        // we need to remove the contentEditable isolation of links
        // before we apply the unlink, otherwise the command is not performed
        // because the content editable root is the link
        const closestEl = closestElement(sel.focusNode, 'a');
        if (closestEl && closestEl.getAttribute('contenteditable') === 'true') {
            editor._activateContenteditable();
        }
        if (sel.isCollapsed) {
            const cr = preserveCursor(editor.document);
            const node = closestElement(sel.focusNode, 'a');
            setSelection(node, 0, node, node.childNodes.length, false);
            editor.document.execCommand('unlink');
            cr();
        } else {
            editor.document.execCommand('unlink');
            setSelection(sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset);
        }
    },

    // List
    indentList: (editor, mode = 'indent') => {
        const [pos1, pos2] = getCursors(editor.document);
        const end = leftLeafFirstPath(...pos1).next().value;
        const li = new Set();
        for (const node of leftLeafFirstPath(...pos2)) {
            const cli = closestBlock(node);
            if (
                cli &&
                cli.tagName == 'LI' &&
                !li.has(cli) &&
                !cli.classList.contains('oe-nested')
            ) {
                li.add(cli);
            }
            if (node == end) break;
        }
        for (const node of li) {
            if (mode == 'indent') {
                node.oTab(0);
            } else {
                node.oShiftTab(0);
            }
        }
        return true;
    },
    toggleList: (editor, mode) => {
        const li = new Set();
        const blocks = new Set();

        for (const node of getTraversedNodes(editor.editable)) {
            if (node.nodeType === Node.TEXT_NODE && !isVisibleStr(node)) {
                node.remove();
            } else {
                const block = closestBlock(node);
                if (!['OL', 'UL'].includes(block.tagName)) {
                    const ublock = block.closest('ol, ul');
                    ublock && getListMode(ublock) == mode ? li.add(block) : blocks.add(block);
                }
            }
        }

        let target = [...(blocks.size ? blocks : li)];
        while (target.length) {
            const node = target.pop();
            // only apply one li per ul
            if (!node.oToggleList(0, mode)) {
                target = target.filter(
                    li => li.parentNode != node.parentNode || li.tagName != 'LI',
                );
            }
        }
    },

    /**
     * Apply a css or class color on the current selection (wrapped in <font>).
     *
     * @param {string} color hexadecimal or bg-name/text-name class
     * @param {string} mode 'color' or 'backgroundColor'
     * @param {Element} [element]
     */
    applyColor: (editor, color, mode, element) => {
        if (element) {
            colorElement(element, color, mode);
            return [element];
        }
        const selection = editor.document.getSelection();
        let wasCollapsed = false;
        if (selection.getRangeAt(0).collapsed) {
            insertAndSelectZws(selection);
            wasCollapsed = true;
        }
        const range = getDeepRange(editor.editable, { splitText: true, select: true });
        if (!range) return;
        const restoreCursor = preserveCursor(editor.document);
        // Get the <font> nodes to color
        const selectedNodes = getSelectedNodes(editor.editable);
        const fonts = selectedNodes.flatMap(node => {
            let font = closestElement(node, 'font');
            const children = font && descendants(font);
            if (font && font.nodeName === 'FONT') {
                // Partially selected <font>: split it.
                const selectedChildren = children.filter(child => selectedNodes.includes(child));
                if (selectedChildren.length) {
                    const splitResult = splitAroundUntil(selectedChildren, font);
                    font = splitResult[0] || splitResult[1] || font;
                } else {
                    font = [];
                }
            } else if (node.nodeType === Node.TEXT_NODE && isVisibleStr(node)) {
                // Node is a visible text node: wrap it in a <font>.
                const previous = node.previousSibling;
                const classRegex = mode === 'color' ? BG_CLASSES_REGEX : TEXT_CLASSES_REGEX;
                if (
                    previous &&
                    previous.nodeName === 'FONT' &&
                    !previous.style[mode === 'color' ? 'backgroundColor' : 'color'] &&
                    !classRegex.test(previous.className) &&
                    selectedNodes.includes(previous.firstChild) &&
                    selectedNodes.includes(previous.lastChild)
                ) {
                    // Directly follows a fully selected <font> that isn't
                    // colored in the other mode: append to that.
                    font = previous;
                } else {
                    // No <font> found: insert a new one.
                    font = document.createElement('font');
                    node.parentNode.insertBefore(font, node);
                }
                font.appendChild(node);
            } else {
                font = []; // Ignore non-text or invisible text nodes.
            }
            return font;
        });
        // Color the selected <font>s and remove uncolored fonts.
        for (const font of new Set(fonts)) {
            colorElement(font, color, mode);
            if (!hasColor(font, mode) && !font.hasAttribute('style')) {
                for (const child of [...font.childNodes]) {
                    font.parentNode.insertBefore(child, font);
                }
                font.parentNode.removeChild(font);
            }
        }
        restoreCursor();
        if (wasCollapsed) {
            const newSelection = editor.document.getSelection();
            const range = new Range();
            range.setStart(newSelection.anchorNode, newSelection.anchorOffset);
            range.collapse(true);
            newSelection.removeAllRanges();
            newSelection.addRange(range);
        }
        return fonts;
    },
    // Table
    insertTable: (editor, { rowNumber = 2, colNumber = 2 } = {}) => {
        const tdsHtml = new Array(colNumber).fill('<td><br></td>').join('');
        const trsHtml = new Array(rowNumber).fill(`<tr>${tdsHtml}</tr>`).join('');
        const tableHtml = `<table class="table table-bordered"><tbody>${trsHtml}</tbody></table>`;
        const sel = editor.document.getSelection();
        if (!sel.isCollapsed) {
            editor.deleteRange(sel);
        }
        while (!isBlock(sel.anchorNode)) {
            const anchorNode = sel.anchorNode;
            const isTextNode = anchorNode.nodeType === Node.TEXT_NODE;
            const newAnchorNode = isTextNode
                ? splitTextNode(anchorNode, sel.anchorOffset, DIRECTIONS.LEFT) + 1 && anchorNode
                : splitElement(anchorNode, sel.anchorOffset).shift();
            const newPosition = rightPos(newAnchorNode);
            setSelection(...newPosition, ...newPosition, false);
        }
        const [table] = editorCommands.insertHTML(editor, tableHtml);
        setCursorStart(table.querySelector('td'));
    },
    addColumnLeft: editor => {
        addColumn(editor, 'before');
    },
    addColumnRight: editor => {
        addColumn(editor, 'after');
    },
    addRowAbove: editor => {
        addRow(editor, 'before');
    },
    addRowBelow: editor => {
        addRow(editor, 'after');
    },
    removeColumn: editor => {
        getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding td.
        const cell = getInSelection(editor.document, 'td');
        if (!cell) return;
        const table = closestElement(cell, 'table');
        const cells = [...closestElement(cell, 'tr').querySelectorAll('th, td')];
        const index = cells.findIndex(td => td === cell);
        const siblingCell = cells[index - 1] || cells[index + 1];
        table.querySelectorAll(`tr td:nth-of-type(${index + 1})`).forEach(td => td.remove());
        siblingCell ? setSelection(...startPos(siblingCell)) : deleteTable(editor, table);
    },
    removeRow: editor => {
        getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding tr.
        const row = getInSelection(editor.document, 'tr');
        if (!row) return;
        const table = closestElement(row, 'table');
        const rows = [...table.querySelectorAll('tr')];
        const rowIndex = rows.findIndex(tr => tr === row);
        const siblingRow = rows[rowIndex - 1] || rows[rowIndex + 1];
        row.remove();
        siblingRow ? setSelection(...startPos(siblingRow)) : deleteTable(editor, table);
    },
    deleteTable: (editor, table) => deleteTable(editor, table),
    insertHorizontalRule(editor) {
        const selection = editor.document.getSelection();
        const range = selection.getRangeAt(0);
        const element = closestElement(
            range.startContainer,
            'P, PRE, H1, H2, H3, H4, H5, H6, BLOCKQUOTE',
        );

        if (element && ancestors(element).includes(editor.editable)) {
            element.before(editor.document.createElement('hr'));
        }
    },
};
