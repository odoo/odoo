/** @odoo-module **/
import { REGEX_BOOTSTRAP_COLUMN } from '../utils/constants.js';
import {
    ancestors,
    descendants,
    childNodeIndex,
    closestBlock,
    closestElement,
    closestPath,
    DIRECTIONS,
    findNode,
    getCursors,
    getDeepRange,
    getInSelection,
    getListMode,
    getSelectedNodes,
    getTraversedNodes,
    insertAndSelectZws,
    insertText,
    isBlock,
    isColorGradient,
    isSelectionFormat,
    isShrunkBlock,
    isSelfClosingElement,
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
    unwrapContents,
    getColumnIndex,
    pxToFloat,
    getRowIndex,
    parseHTML,
    formatSelection,
    getDeepestPosition,
    fillEmpty,
    isEmptyBlock,
    isWhitespace,
    isVisibleTextNode,
    getCursorDirection,
    resetOuids,
    FONT_SIZE_CLASSES,
    TEXT_STYLE_CLASSES,
    padLinkWithZws,
    isLinkEligibleForZwnbsp,
    paragraphRelatedElements,
    lastLeaf,
    firstLeaf,
    convertList,
} from '../utils/utils.js';

const TEXT_CLASSES_REGEX = /\btext-[^\s]*\b/;
const BG_CLASSES_REGEX = /\bbg-[^\s]*\b/;

function align(editor, mode) {
    const sel = editor.document.getSelection();
    const visitedBlocks = new Set();
    const traversedNode = getTraversedNodes(editor.editable);
    for (const node of traversedNode) {
        if (isVisibleTextNode(node)) {
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
        (style[mode] && style[mode] !== 'inherit' && (!parent || style[mode] !== parent.style[mode])) ||
        (classRegex.test(element.className) &&
            (!parent || getComputedStyle(element)[mode] !== getComputedStyle(parent)[mode]))
    );
}

// This is a whitelist of the commands that are implemented by the
// editor itself rather than the node prototypes. It might be
// possible to switch the conditions and test if the method exist on
// `sel.anchorNode` rather than relying on an expicit whitelist, but
// the behavior would change if a method name exists both on the
// editor and on the nodes. This is too risky to change in the
// absence of a strong test suite, so the whitelist stays for now.
export const editorCommands = {
    insert: (editor, content) => {
        if (!content) return;
        const selection = editor.document.getSelection();
        let startNode;
        let insertBefore = false;
        if (!selection.isCollapsed) {
            editor.deleteRange(selection);
        }
        const range = selection.getRangeAt(0);
        const block = closestBlock(selection.anchorNode);
        const isSelectionAtStart = firstLeaf(block) === selection.anchorNode && selection.anchorOffset === 0;
        const isSelectionAtEnd = lastLeaf(block) === selection.focusNode && selection.focusOffset === nodeSize(selection.focusNode);
        if (range.startContainer.nodeType === Node.TEXT_NODE) {
            insertBefore = !range.startOffset;
            splitTextNode(range.startContainer, range.startOffset, DIRECTIONS.LEFT);
            startNode = range.startContainer;
        }

        const container = document.createElement('fake-element');
        const containerFirstChild = document.createElement('fake-element-fc');
        const containerLastChild = document.createElement('fake-element-lc');

        if (typeof content === 'string') {
            container.textContent = content;
        } else {
            container.replaceChildren(content);
        }

        // In case the html inserted starts with a list and will be inserted within
        // a list, unwrap the list elements from the list.
        const isList = node => ['UL', 'OL'].includes(node.nodeName);
        const hasSingleChild = container.childNodes.length === 1;
        if (
            closestElement(selection.anchorNode, 'UL, OL') &&
            isList(container.firstChild)
        ) {
            unwrapContents(container.firstChild);
        }
        // Similarly if the html inserted ends with a list.
        if (
            closestElement(selection.focusNode, 'UL, OL') &&
            isList(container.lastChild) &&
            !hasSingleChild
        ) {
            unwrapContents(container.lastChild);
        }

        startNode = startNode || editor.document.getSelection().anchorNode;
        const shouldUnwrap = (node) => (
            [...paragraphRelatedElements, 'LI'].includes(node.nodeName) &&
            block.textContent !== "" && node.textContent !== "" &&
            (
                block.nodeName === node.nodeName ||
                ['BLOCKQUOTE', 'PRE', 'DIV'].includes(block.nodeName)
            ) && selection.anchorNode.oid !== 'root'
        );

        // Empty block must contain a br element to allow cursor placement.
        if (
            container.lastElementChild &&
            isBlock(container.lastElementChild) &&
            !container.lastElementChild.hasChildNodes()
        ) {
            fillEmpty(container.lastElementChild);
        }

        // In case the html inserted is all contained in a single root <p> or <li>
        // tag, we take the all content of the <p> or <li> and avoid inserting the
        // <p> or <li>. The same is true for a <pre> inside a <pre>.
        if (
            container.childElementCount === 1 &&
            (
                ['P', 'LI'].includes(container.firstChild.nodeName) ||
                shouldUnwrap(container.firstChild)
            ) && selection.anchorNode.oid !== 'root'
        ) {
            const p = container.firstElementChild;
            container.replaceChildren(...p.childNodes);
        } else if (container.childElementCount > 1) {
            // Grab the content of the first child block and isolate it.
            if (shouldUnwrap(container.firstChild) && !isSelectionAtStart) {
                // Unwrap the deepest nested first <li> element in the
                // container to extract and paste the text content of the list.
                if (container.firstChild.nodeName === 'LI') {
                    const deepestBlock = closestBlock(firstLeaf(container.firstChild));
                    splitAroundUntil(deepestBlock, container.firstChild);
                    container.firstElementChild.replaceChildren(...deepestBlock.childNodes);
                }
                containerFirstChild.replaceChildren(...container.firstElementChild.childNodes);
                container.firstElementChild.remove();
            }
            // Grab the content of the last child block and isolate it.
            if (shouldUnwrap(container.lastChild) && !isSelectionAtEnd) {
                // Unwrap the deepest nested last <li> element in the container
                // to extract and paste the text content of the list.
                if (container.lastChild.nodeName === 'LI') {
                    const deepestBlock = closestBlock(lastLeaf(container.lastChild));
                    splitAroundUntil(deepestBlock, container.lastChild);
                    container.lastElementChild.replaceChildren(...deepestBlock.childNodes);
                }
                containerLastChild.replaceChildren(...container.lastElementChild.childNodes);
                container.lastElementChild.remove();
            }
        }

        if (startNode.nodeType === Node.ELEMENT_NODE) {
            if (selection.anchorOffset === 0) {
                const textNode = editor.document.createTextNode('');
                if (isSelfClosingElement(startNode)) {
                    startNode.parentNode.insertBefore(textNode, startNode);
                } else {
                    startNode.prepend(textNode);
                }
                startNode = textNode;
            } else {
                startNode = startNode.childNodes[selection.anchorOffset - 1];
            }
        }

        // If we have isolated block content, first we split the current focus
        // element if it's a block then we insert the content in the right places.
        let currentNode = startNode;
        let lastChildNode = false;
        const currentList = currentNode && closestElement(currentNode, 'UL, OL');
        const mode = currentList && getListMode(currentList);

        const _insertAt = (reference, nodes, insertBefore) => {
            for (const child of (insertBefore ? nodes.reverse() : nodes)) {
                reference[insertBefore ? 'before' : 'after'](child);
                reference = child;
            }
        }
        const lastInsertedNodes = [...containerLastChild.childNodes];
        if (containerLastChild.hasChildNodes()) {
            const toInsert = [...containerLastChild.childNodes]; // Prevent mutation
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = insertBefore ? toInsert[0] : currentNode;
            lastChildNode = toInsert[toInsert.length - 1];
        }
        const firstInsertedNodes = [...containerFirstChild.childNodes];
        if (containerFirstChild.hasChildNodes()) {
            const toInsert = [...containerFirstChild.childNodes]; // Prevent mutation
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = toInsert[toInsert.length - 1];
            insertBefore = false;
        }

        // If all the Html have been isolated, We force a split of the parent element
        // to have the need new line in the final result
        if (!container.hasChildNodes()) {
            if (isUnbreakable(closestBlock(currentNode.nextSibling))) {
                currentNode.nextSibling.oShiftEnter(0);
            } else {
                // If we arrive here, the o_enter index should always be 0.
                const parent = currentNode.nextSibling.parentElement;
                const index = [...parent.childNodes].indexOf(currentNode.nextSibling);
                parent.oEnter(index);
            }
        }

        let nodeToInsert;
        const insertedNodes = [...container.childNodes];
        while ((nodeToInsert = container.childNodes[0])) {
            if (isBlock(nodeToInsert) && !allowsParagraphRelatedElements(currentNode)) {
                // Split blocks at the edges if inserting new blocks (preventing
                // <p><p>text</p></p> or <li><li>text</li></li> scenarios).
                while (
                    currentNode.parentElement !== editor.editable &&
                    (!allowsParagraphRelatedElements(currentNode.parentElement) ||
                        (currentNode.parentElement.nodeName === 'LI' && nodeToInsert.nodeName !== 'TABLE'))
                ) {
                    if (isUnbreakable(currentNode.parentElement)) {
                        makeContentsInline(container);
                        nodeToInsert = container.childNodes[0];
                        break;
                    }
                    let offset = childNodeIndex(currentNode);
                    if (!insertBefore) {
                        offset += 1;
                    }
                    if (offset) {
                        const [left, right] = splitElement(currentNode.parentElement, offset);
                        if (isUnbreakable(nodeToInsert) && container.childNodes.length === 1) {
                            fillEmpty(right);
                        } else if (isEmptyBlock(right)) {
                            right.remove();
                        }
                        currentNode = insertBefore ? right : left;
                    } else {
                        currentNode = currentNode.parentElement;
                    }
                }
                if (currentNode.parentElement.nodeName === 'LI' && nodeToInsert.nodeName === 'TABLE') {
                    const br = document.createElement('br');
                    currentNode[currentNode.textContent ? 'after' : 'before'](br);
                }
            }
            // Ensure that all adjacent paragraph elements are converted to
            // <li> when inserting in a list.
            if (block.nodeName === "LI" && paragraphRelatedElements.includes(nodeToInsert.nodeName)) {
                setTagName(nodeToInsert, "LI");
            }
            // Contenteditable false property changes to true after the node is
            // inserted into DOM.
            const isNodeToInsertContentEditable = nodeToInsert.isContentEditable;
            if (insertBefore) {
                currentNode.before(nodeToInsert);
                insertBefore = false;
            } else {
                currentNode.after(nodeToInsert);
            }
            if (
                ['BLOCKQUOTE', 'PRE'].includes(block.nodeName) &&
                paragraphRelatedElements.includes(nodeToInsert.nodeName)
            ) {
                nodeToInsert = setTagName(nodeToInsert, block.nodeName);
            }
            let convertedList;
            if (
                currentList &&
                (
                    (nodeToInsert.nodeName === 'LI' && nodeToInsert.classList.contains('oe-nested')) ||
                    isList(nodeToInsert)
                )
            ) {
                convertedList = convertList(nodeToInsert, mode);
            }
            if (currentNode.tagName !== 'BR' && isShrunkBlock(currentNode)) {
                currentNode.remove();
            }
            // If the first child of editable is contenteditable false element
            // a chromium bug prevents selecting the container. Prepend a
            // zero-width space so it's no longer the first child.
            if (
                !isNodeToInsertContentEditable &&
                editor.editable.firstChild === nodeToInsert &&
                nodeToInsert.nodeName === 'DIV'
            ) {
                const zws = document.createTextNode('\u200B');
                nodeToInsert.before(zws);
            }
            currentNode = convertedList || nodeToInsert;
        }

        currentNode = lastChildNode || currentNode;
        if (
            !isUnbreakable(currentNode) &&
            currentNode.nodeName !== 'BR' &&
            currentNode.nextSibling &&
            currentNode.nextSibling.nodeName === 'BR' &&
            lastLeaf(currentNode.parentNode) === currentNode.nextSibling &&
            !closestElement(currentNode, '[t-field],[t-esc],[t-out]')
        ) {
            currentNode.nextSibling.remove();
        }
        selection.removeAllRanges();
        const newRange = new Range();
        let lastPosition;
        if (currentNode.nodeName === 'A' && isLinkEligibleForZwnbsp(editor.editable, currentNode)) {
            padLinkWithZws(editor.editable, currentNode);
            currentNode = currentNode.nextSibling;
            lastPosition = getDeepestPosition(...rightPos(currentNode));
        } else {
            lastPosition = [...paragraphRelatedElements, 'LI', 'UL', 'OL'].includes(currentNode.nodeName)
                ? rightPos(lastLeaf(currentNode))
                : rightPos(currentNode);
        }
        if (!editor.options.allowInlineAtRoot && lastPosition[0] === editor.editable) {
            // Correct the position if it happens to be in the editable root.
            lastPosition = getDeepestPosition(...lastPosition);
        }
        newRange.setStart(lastPosition[0], lastPosition[1]);
        newRange.setEnd(lastPosition[0], lastPosition[1]);
        selection.addRange(newRange);
        return [...firstInsertedNodes, ...insertedNodes, ...lastInsertedNodes];
    },
    insertFontAwesome: (editor, faClass = 'fa fa-star') => {
        const insertedNode = editorCommands.insert(editor, document.createElement('i'))[0];
        insertedNode.className = faClass;
        const position = rightPos(insertedNode);
        setSelection(...position, ...position, false);
    },

    // History
    undo: editor => editor.historyUndo(),
    redo: editor => editor.historyRedo(),

    // Change tags
    setTag(editor, tagName, extraClass = "") {
        const range = getDeepRange(editor.editable, { correctTripleClick: true });
        const selectedBlocks = [...new Set(getTraversedNodes(editor.editable, range).map(closestBlock))];
        const deepestSelectedBlocks = selectedBlocks.filter(block => (
            !descendants(block).some(descendant => selectedBlocks.includes(descendant)) &&
            block.isContentEditable
        ));
        let { startContainer, startOffset, endContainer, endOffset } = range;
        const startContainerChild = startContainer.firstChild;
        const endContainerChild = endContainer.lastChild;
        for (const block of deepestSelectedBlocks) {
            if (
                ['P', 'PRE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI', 'BLOCKQUOTE'].includes(
                    block.nodeName,
                )
            ) {
                const inLI = block.closest('li');
                if (inLI && tagName === "P") {
                    inLI.oToggleList(0);
                } else {
                    const newEl = setTagName(block, tagName);
                    newEl.classList.remove(
                        ...FONT_SIZE_CLASSES,
                        ...TEXT_STYLE_CLASSES,
                        // We want to be able to edit the case `<h2 class="h3">`
                        // but in that case, we want to display "Header 2" and
                        // not "Header 3" as it is more important to display
                        // the semantic tag being used (especially for h1 ones).
                        // This is why those are not in `TEXT_STYLE_CLASSES`.
                        "h1", "h2", "h3", "h4", "h5", "h6"
                    );
                    delete newEl.style.fontSize;
                    if (extraClass) {
                        newEl.classList.add(extraClass);
                    }
                    if (newEl.classList.length === 0) {
                        newEl.removeAttribute("class");
                    }
                }
            } else {
                // eg do not change a <div> into a h1: insert the h1
                // into it instead.
                const newBlock = editor.document.createElement(tagName);
                const children = [...block.childNodes];
                block.insertBefore(newBlock, block.firstChild);
                children.forEach(child => newBlock.appendChild(child));
            }
        }
        const isContextBlock = container => ['TD', 'DIV', 'LI'].includes(container.nodeName);
        if (!startContainer.isConnected || isContextBlock(startContainer)) {
            startContainer = startContainerChild.parentNode;
        }
        if (!endContainer.isConnected || isContextBlock(endContainer)) {
            endContainer = endContainerChild.parentNode;
        }
        const newRange = new Range();
        newRange.setStart(startContainer, startOffset);
        newRange.setEnd(endContainer, endOffset);
        getDeepRange(editor.editable, { range: newRange, select: true });
        editor.historyStep();
    },

    // Formats
    // -------------------------------------------------------------------------
    bold: editor => formatSelection(editor, 'bold'),
    italic: editor => formatSelection(editor, 'italic'),
    underline: editor => formatSelection(editor, 'underline'),
    strikeThrough: editor => formatSelection(editor, 'strikeThrough'),
    setFontSize: (editor, size) => formatSelection(editor, 'fontSize', {applyStyle: true, formatProps: {size}}),
    setFontSizeClassName: (editor, className) => formatSelection(editor, 'setFontSizeClassName', {formatProps: {className}}),
    switchDirection: editor => {
        getDeepRange(editor.editable, { splitText: true, select: true, correctTripleClick: true });
        const selection = editor.document.getSelection();
        const selectedTextNodes = [selection.anchorNode, ...getSelectedNodes(editor.editable), selection.focusNode]
            .filter(n => n.nodeType === Node.TEXT_NODE && closestElement(n).isContentEditable && n.nodeValue.trim().length);

        const changedElements = [];
        const defaultDirection = editor.options.direction;
        const shouldApplyStyle = !isSelectionFormat(editor.editable, 'switchDirection');
        let blocks = new Set(selectedTextNodes.map(textNode => closestElement(textNode, 'ul,ol') || closestBlock(textNode)));
        blocks.forEach(block => {
            blocks = [...blocks, ...block.querySelectorAll('ul,ol')];
        })
        for (const block of blocks) {
            if (!shouldApplyStyle) {
                block.removeAttribute('dir');
            } else {
                block.setAttribute('dir', defaultDirection === 'ltr' ? 'rtl' : 'ltr');
            }
            changedElements.push(block);
        }

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
        const textAlignStyles = new Map();
        getTraversedNodes(editor.editable).forEach((element) => {
            const block = closestBlock(element);
            if (block.style.textAlign) {
                textAlignStyles.set(block, block.style.textAlign);
            }
        });
        // Calling `document.execCommand` will cause an input event with the
        // input type "formatRemove". This would cause a new history step to be
        // created in the middle of the process, which we prevent here.
        editor.historyPauseSteps();
        editor.document.execCommand('removeFormat');
        for (const node of getTraversedNodes(editor.editable)) {
            if (node.nodeType === Node.ELEMENT_NODE && node.hasAttribute('color')) {
                node.removeAttribute('color');
            }
            const element = closestElement(node);
            element.style.removeProperty('color');
            element.style.removeProperty('background');
        }
        textAlignStyles.forEach((textAlign, block) => {
            block.style.setProperty('text-align', textAlign);
        });
        editor.historyUnpauseSteps();
    },

    // Align
    justifyLeft: editor => align(editor, 'left'),
    justifyRight: editor => align(editor, 'right'),
    justifyCenter: editor => align(editor, 'center'),
    justifyFull: editor => align(editor, 'justify'),

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
        const isCollapsed = sel.isCollapsed;
        // If the selection is collapsed, unlink the whole link:
        // `<a>a[]b</a>` => `a[]b`.
        getDeepRange(editor.editable, { sel, splitText: true, select: true });
        if (!isCollapsed) {
            // If not, unlink only the part(s) of the link(s) that are selected:
            // `<a>a[b</a>c<a>d</a>e<a>f]g</a>` => `<a>a</a>[bcdef]<a>g</a>`.
            let { anchorNode, focusNode, anchorOffset, focusOffset } = sel;
            const direction = getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset);
            // Split the links around the selection.
            const [startLink, endLink] = [closestElement(anchorNode, 'a'), closestElement(focusNode, 'a')];
            if (startLink) {
                anchorNode = splitAroundUntil(anchorNode, startLink);
                anchorOffset = direction === DIRECTIONS.RIGHT ? 0 : nodeSize(anchorNode);
                setSelection(anchorNode, anchorOffset, focusNode, focusOffset, true);
            }
            // Only split the end link if it was not already done above.
            if (endLink && endLink.isConnected) {
                focusNode = splitAroundUntil(focusNode, endLink);
                focusOffset = direction === DIRECTIONS.RIGHT ? nodeSize(focusNode) : 0;
                setSelection(anchorNode, anchorOffset, focusNode, focusOffset, true);
            }
        }
        const targetedNodes = isCollapsed ? [sel.anchorNode] : getSelectedNodes(editor.editable);
        const links = new Set(targetedNodes.map(node => closestElement(node, 'a')).filter(a => a && a.isContentEditable));
        if (links.size) {
            const cr = preserveCursor(editor.document);
            for (const link of links) {
                unwrapContents(link);
            }
            cr();
        }
    },

    // List
    indentList: (editor, mode = 'indent') => {
        const [pos1, pos2] = getCursors(editor.document);
        const end = leftLeafFirstPath(...pos1).next().value;
        const li = new Set();
        for (const node of leftLeafFirstPath(...pos2)) {
            const cli = closestElement(node,'li');
            if (
                cli &&
                cli.tagName == 'LI' &&
                !li.has(cli) &&
                !cli.classList.contains('oe-nested') &&
                cli.isContentEditable &&
                !cli.classList.contains('nav-item')
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

        const selectedBlocks = getTraversedNodes(editor.editable);
        const deepestSelectedBlocks = selectedBlocks.filter(block => (
            !descendants(block).some(descendant => selectedBlocks.includes(descendant))
        ));
        for (const node of deepestSelectedBlocks) {
            let nodeToToggle = closestBlock(node);
            if (
                ![...paragraphRelatedElements, 'LI'].includes(nodeToToggle.nodeName) &&
                node.nodeType === Node.TEXT_NODE && isWhitespace(node) && closestElement(node).isContentEditable
            ) {
                node.remove();
            } else {
                // Ensure nav-item lists are excluded from toggling
                const isNavItemList = node => node.nodeName === 'LI' && node.classList.contains('nav-item');
                nodeToToggle = isNavItemList(nodeToToggle) ? node : nodeToToggle;
                if (!['OL', 'UL'].includes(nodeToToggle.tagName) && (nodeToToggle.isContentEditable || nodeToToggle.nodeType === Node.TEXT_NODE)) {
                    const closestLi = closestElement(nodeToToggle, 'li');
                    nodeToToggle = closestLi && !isNavItemList(closestLi) ? closestLi : nodeToToggle;
                    const ublock = nodeToToggle.nodeName === 'LI' && nodeToToggle.closest('ol, ul');
                    ublock && getListMode(ublock) == mode ? li.add(nodeToToggle) : blocks.add(nodeToToggle);
                }
            }
        }

        let target = [...(blocks.size ? blocks : li)];
        if (blocks.size) {
            // Remove hardcoded padding to have default padding of list element 
            for (const block of blocks) {
                if (block.style) {
                    block.style.padding = "";
                }
            }
        }
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
        const selectedTds = [...editor.editable.querySelectorAll('td.o_selected_td')].filter(
            node => closestElement(node).isContentEditable
        );
        let coloredTds = [];
        if (selectedTds.length && mode === "backgroundColor") {
            for (const td of selectedTds) {
                colorElement(td, color, mode);
            }
            coloredTds = [...selectedTds];
        } else if (element) {
            colorElement(element, color, mode);
            return [element];
        }
        const selection = editor.document.getSelection();
        let wasCollapsed = false;
        if (selection.getRangeAt(0).collapsed && !selectedTds.length) {
            insertAndSelectZws(selection);
            wasCollapsed = true;
        }
        const range = getDeepRange(editor.editable, { splitText: true, select: true });
        if (!range) return;
        const restoreCursor = preserveCursor(editor.document);
        // Get the <font> nodes to color
        const selectionNodes = getSelectedNodes(editor.editable).filter(node => closestElement(node).isContentEditable && node.nodeName !== "T");
        if (isEmptyBlock(range.endContainer)) {
            selectionNodes.push(range.endContainer, ...descendants(range.endContainer));
        }
        const selectedNodes = mode === "backgroundColor"
            ? selectionNodes.filter(node => !closestElement(node, 'table.o_selected_table'))
            : selectionNodes;
        const selectedFieldNodes = new Set(getSelectedNodes(editor.editable)
                .map(n => closestElement(n, "*[t-field],*[t-out],*[t-esc]"))
                .filter(Boolean));

        function getFonts(selectedNodes) {
            return selectedNodes.flatMap(node => {
                let font = closestElement(node, 'font') || closestElement(node, 'span');
                const children = font && descendants(font);
                if (font && (font.nodeName === 'FONT' || (font.nodeName === 'SPAN' && font.style[mode]))) {
                    // Partially selected <font>: split it.
                    const selectedChildren = children.filter(child => selectedNodes.includes(child));
                    if (selectedChildren.length) {
                        font = splitAroundUntil(selectedChildren, font);
                    } else {
                        font = [];
                    }
                } else if ((node.nodeType === Node.TEXT_NODE && !isWhitespace(node) && node.textContent !== '\ufeff')
                        || (node.nodeName === 'BR' && isEmptyBlock(node.parentNode))
                        || (node.nodeType === Node.ELEMENT_NODE &&
                            node.nodeName !== 'FIGURE' &&
                            ['inline', 'inline-block'].includes(getComputedStyle(node).display) &&
                            !isWhitespace(node.textContent) &&
                            !node.classList.contains('btn') &&
                            !node.querySelector('font')) &&
                            node.nodeName !== 'A' &&
                            !(node.nodeName === 'SPAN' && node.style['fontSize'])) {
                    // Node is a visible text or inline node without font nor a button:
                    // wrap it in a <font>.
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
                        node.after(font);
                    }
                    if (node.textContent) {
                        font.appendChild(node);
                    } else {
                        fillEmpty(font);
                    }
                } else {
                    font = []; // Ignore non-text or invisible text nodes.
                }
                return font;
            });
        }

        for (const fieldNode of selectedFieldNodes) {
            colorElement(fieldNode, color, mode);
        }

        let fonts = getFonts(selectedNodes);
        // Dirty fix as the previous call could have unconnected elements
        // because of the `splitAroundUntil`. Another call should provide he
        // correct list of fonts.
        if (!fonts.every((font) => font.isConnected)) {
            fonts = getFonts(selectedNodes);
        }

        // Color the selected <font>s and remove uncolored fonts.
        const fontsSet = new Set(fonts);
        for (const font of fontsSet) {
            colorElement(font, color, mode);
            if ((!hasColor(font, 'color') && !hasColor(font,'backgroundColor')) && (!font.hasAttribute('style') || !color)) {
                for (const child of [...font.childNodes]) {
                    font.parentNode.insertBefore(child, font);
                }
                font.parentNode.removeChild(font);
                fontsSet.delete(font);
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
        return [...fontsSet, ...coloredTds];
    },
    // Table
    insertTable: (editor, { rowNumber = 2, colNumber = 2 } = {}) => {
        const tdsHtml = new Array(colNumber).fill('<td><p><br></p></td>').join('');
        const trsHtml = new Array(rowNumber).fill(`<tr>${tdsHtml}</tr>`).join('');
        const tableHtml = `<table class="table table-bordered o_table"><tbody>${trsHtml}</tbody></table>`;
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
        const [table] = editorCommands.insert(editor, parseHTML(editor.document, tableHtml));
        setCursorStart(table.querySelector('p'));
    },
    addColumn: (editor, beforeOrAfter, referenceCell) => {
        if (!referenceCell) {
            getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding td.
            referenceCell = getInSelection(editor.document, 'td');
            if (!referenceCell) return;
        }
        const columnIndex = getColumnIndex(referenceCell);
        const table = closestElement(referenceCell, 'table');
        const tableWidth = table.style.width ? pxToFloat(table.style.width) : table.clientWidth;
        const referenceColumn = table.querySelectorAll(`tr td:nth-of-type(${columnIndex + 1})`);
        const referenceCellWidth = referenceCell.style.width ? pxToFloat(referenceCell.style.width) : referenceCell.clientWidth;
        // Temporarily set widths so proportions are respected.
        const firstRow = table.querySelector('tr');
        const firstRowCells = [...firstRow.children].filter(child => child.nodeName === 'TD' || child.nodeName === 'TH');
        let totalWidth = 0;
        for (const cell of firstRowCells) {
            const width = cell.style.width ? pxToFloat(cell.style.width) : cell.clientWidth;
            cell.style.width = width + 'px';
            // Spread the widths to preserve proportions.
            // -1 for the width of the border of the new column.
            const newWidth = Math.max(Math.round((width * tableWidth) / (tableWidth + referenceCellWidth - 1)), 13);
            cell.style.width = newWidth + 'px';
            totalWidth += newWidth;
        }
        referenceColumn.forEach((cell, rowIndex) => {
            const newCell = document.createElement('td');
            const p = document.createElement('p');
            p.append(document.createElement('br'));
            newCell.append(p);
            cell[beforeOrAfter](newCell);
            if (rowIndex === 0) {
                newCell.style.width = cell.style.width;
                totalWidth += pxToFloat(cell.style.width);
            }
        });
        if (totalWidth !== tableWidth - 1) { // -1 for the width of the border of the new column.
            firstRowCells[firstRowCells.length - 1].style.width = pxToFloat(firstRowCells[firstRowCells.length - 1].style.width) + (tableWidth - totalWidth - 1) + 'px';
        }
        // Fix the table and row's width so it doesn't change.
        table.style.width = tableWidth + 'px';
    },
    addRow: (editor, beforeOrAfter, referenceRow) => {
        if (!referenceRow) {
            getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding tr.
            referenceRow = getInSelection(editor.document, 'tr');
            if (!referenceRow) return;
        }
        const referenceRowHeight = referenceRow.style.height ? pxToFloat(referenceRow.style.height) : referenceRow.clientHeight;
        const newRow = document.createElement('tr');
        newRow.style.height = referenceRowHeight + 'px';
        const cells = referenceRow.querySelectorAll('td');
        newRow.append(...Array.from(Array(cells.length)).map(() => {
            const td = document.createElement('td');
            const p = document.createElement('p');
            p.append(document.createElement('br'));
            td.append(p);
            return td;
        }));
        referenceRow[beforeOrAfter](newRow);
        newRow.style.height = referenceRowHeight + 'px';
        if (getRowIndex(newRow) === 0) {
            let columnIndex = 0;
            for (const newColumn of newRow.children) {
                newColumn.style.width = cells[columnIndex].style.width;
                cells[columnIndex].style.width = '';
                columnIndex++;
            }
        }
    },
    removeColumn: (editor, cell) => {
        if (!cell) {
            getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding td.
            cell = getInSelection(editor.document, 'td');
            if (!cell) return;
        }
        const table = closestElement(cell, 'table');
        const cells = [...closestElement(cell, 'tr').querySelectorAll('th, td')];
        const index = cells.findIndex(td => td === cell);
        const siblingCell = cells[index - 1] || cells[index + 1];
        if (table.style.width) {
            const tableRect = table.getBoundingClientRect();
            const cellRect = cell.getBoundingClientRect();
            table.style.width = tableRect.width - cellRect.width + 'px';
        }
        table.querySelectorAll(`tr td:nth-of-type(${index + 1})`).forEach(td => td.remove());
        siblingCell ? setSelection(...startPos(siblingCell)) : editorCommands.deleteTable(editor, table);
    },
    removeRow: (editor, row) => {
        if (!row) {
            getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding tr.
            row = getInSelection(editor.document, 'tr');
            if (!row) return;
        }
        const table = closestElement(row, 'table');
        const rows = [...table.querySelectorAll('tr')];
        const rowIndex = rows.findIndex(tr => tr === row);
        const siblingRow = rows[rowIndex - 1] || rows[rowIndex + 1];
        row.remove();
        siblingRow ? setSelection(...startPos(siblingRow)) : editorCommands.deleteTable(editor, table);
    },
    resetSize: (editor,table) => {
        if (!table) {
            getDeepRange(editor.editable, { select: true });
            table = getInSelection(editor.document,'table');
        }
        table.removeAttribute('style');
        const cells = [...table.querySelectorAll('tr, td')];
        cells.forEach( cell => {
            const cStyle = cell.style;
            if (cell.tagName === 'TR') {
                cStyle.height = '';
            } else {
                cStyle.width = '';
            }
        })
    },
    deleteTable: (editor, table) => {
        table = table || getInSelection(editor.document, 'table');
        if (!table) return;
        const p = document.createElement('p');
        p.appendChild(document.createElement('br'));
        table.before(p);
        table.remove();
        setSelection(p, 0);
    },
    // Structure
    columnize: (editor, numberOfColumns, addParagraphAfter=true) => {
        const sel = editor.document.getSelection();
        const anchor = sel.anchorNode;
        const hasColumns = !!closestElement(anchor, '.o_text_columns');
        if (!numberOfColumns && hasColumns) {
            // Remove columns.
            const restore = preserveCursor(editor.document);
            const container = closestElement(anchor, '.o_text_columns');
            const rows = unwrapContents(container);
            for (const row of rows) {
                const columns = unwrapContents(row);
                for (const column of columns) {
                    const columnContents = unwrapContents(column);
                    for (const node of columnContents) {
                        resetOuids(node);
                    }
                }
            }
            restore();
        } else if (numberOfColumns && !hasColumns) {
            // Create columns.
            const restore = preserveCursor(editor.document);
            const container = document.createElement('div');
            if (!closestElement(anchor, '.container')) {
                container.classList.add('container');
            }
            container.classList.add('o_text_columns');
            const row = document.createElement('div');
            row.classList.add('row');
            container.append(row);
            const block = closestBlock(anchor);
            resetOuids(block);
            const columnSize = Math.floor(12 / numberOfColumns);
            const columns = [];
            for (let i = 0; i < numberOfColumns; i++) {
                const column = document.createElement('div');
                column.classList.add(`col-${columnSize}`);
                row.append(column);
                columns.push(column);
            }
            block.before(container);
            columns.shift().append(block);
            for (const column of columns) {
                const p = document.createElement('p');
                p.append(document.createElement('br'));
                p.classList.add('oe-hint');
                p.setAttribute('placeholder', 'New column...');
                column.append(p);
            }
            restore();
            if (addParagraphAfter) {
                const p = document.createElement('p');
                p.append(document.createElement('br'));
                container.after(p);
            }
        } else if (numberOfColumns && hasColumns) {
            const row = closestElement(anchor, '.row');
            const columns = [...row.children];
            const columnSize = Math.floor(12 / numberOfColumns);
            const diff = numberOfColumns - columns.length;
            if (diff > 0) {
                // Add extra columns.
                const restore = preserveCursor(editor.document);
                for (const column of columns) {
                    column.className = column.className.replace(REGEX_BOOTSTRAP_COLUMN, `col$1-${columnSize}`);
                }
                let lastColumn = columns[columns.length - 1];
                for (let i = 0; i < diff; i++) {
                    const column = document.createElement('div');
                    column.classList.add(`col-${columnSize}`);
                    const p = document.createElement('p');
                    p.append(document.createElement('br'));
                    p.classList.add('oe-hint');
                    p.setAttribute('placeholder', 'New column...');
                    column.append(p);
                    lastColumn.after(column);
                    lastColumn = column;
                }
                restore();
            } else if (diff < 0) {
                // Remove superfluous columns.
                const restore = preserveCursor(editor.document);
                for (const column of columns) {
                    column.className = column.className.replace(REGEX_BOOTSTRAP_COLUMN, `col$1-${columnSize}`);
                }
                const contents = [];
                for (let i = diff; i < 0; i++) {
                    const column = columns.pop();
                    const columnContents = unwrapContents(column);
                    for (const node of columnContents) {
                        resetOuids(node);
                    }
                    contents.unshift(...columnContents);
                }
                columns[columns.length - 1].append(...contents);
                restore();
            }
        }
    },
    insertHorizontalRule(editor) {
        const selection = editor.document.getSelection();
        const range = selection.getRangeAt(0);
        const element = closestElement(range.startContainer, paragraphRelatedElements) || closestBlock(range.startContainer);

        if (element && ancestors(element).includes(editor.editable)) {
            element.before(editor.document.createElement('hr'));
        }
    },
};
