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
    isContentTextNode,
    isSelectionFormat,
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
    unwrapContents,
    getColumnIndex,
    pxToFloat,
    getRowIndex,
    parseHTML,
    formatSelection,
} from '../utils/utils.js';

const TEXT_CLASSES_REGEX = /\btext-[^\s]*\b/g;
const BG_CLASSES_REGEX = /\bbg-[^\s]*\b/g;

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

        const container = document.createElement('fake-element');
        const containerFirstChild = document.createElement('fake-element-fc');
        const containerLastChild = document.createElement('fake-element-lc');

        if (content instanceof Node) {
            container.replaceChildren(content);
        } else {
            container.textContent = content;
        }

        // In case the html inserted starts with a list and will be inserted within
        // a list, unwrap the list elements from the list.
        if (closestElement(selection.anchorNode, 'UL, OL') &&
            (container.firstChild.nodeName === 'UL' || container.firstChild.nodeName === 'OL')) {
            container.replaceChildren(...container.firstChild.childNodes);
        }

        // In case the html inserted is all contained in a single root <p> or <li>
        // tag, we take the all content of the <p> or <li> and avoid inserting the
        // <p> or <li>.
        if (container.childElementCount === 1 && (container.firstChild.nodeName === 'P' || container.firstChild.nodeName === 'LI')) {
            const p = container.firstElementChild;
            container.replaceChildren(...p.childNodes);
        } else if (container.childElementCount > 1) {
            // Grab the content of the first child block and isolate it.
            if (isBlock(container.firstChild)) {
                containerFirstChild.replaceChildren(...container.firstElementChild.childNodes);
                container.firstElementChild.remove();
            }
            // Grab the content of the last child block and isolate it.
            if (isBlock(container.lastChild)) {
                containerLastChild.replaceChildren(...container.lastElementChild.childNodes);
                container.lastElementChild.remove();
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
        if (containerLastChild.hasChildNodes()) {
            const toInsert = [...containerLastChild.childNodes]; // Prevent mutation
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = insertBefore ? toInsert[0] : currentNode;
            lastChildNode = toInsert[toInsert.length - 1];
        }
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
                currentNode.nextSibling.parentElement.oEnter(index);
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
                        currentNode.parentElement.nodeName === 'LI')
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
    setTag(editor, tagName) {
        const restoreCursor = preserveCursor(editor.document);
        const range = getDeepRange(editor.editable, { correctTripleClick: true });
        const selectedBlocks = [...new Set(getTraversedNodes(editor.editable, range).map(closestBlock))];
        for (const block of selectedBlocks) {
            if (
                ['P', 'PRE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI', 'BLOCKQUOTE'].includes(
                    block.nodeName,
                )
            ) {
                setSelection(block, 0, block, nodeSize(block));
                editor.historyPauseSteps();
                // Keep the alignment and remove rest of the applied styles.
                const textAlign = block.style.textAlign;
                editor.execCommand('removeFormat');
                if (textAlign) {
                    block.style.textAlign = textAlign;
                }
                editor.historyUnpauseSteps();
                const inLI = block.closest('li');
                if (inLI && tagName === "P") {
                    inLI.oToggleList(0);
                } else {
                    setTagName(block, tagName);
                }
            }  else {
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
    bold: editor => formatSelection(editor, 'bold'),
    italic: editor => formatSelection(editor, 'italic'),
    underline: editor => formatSelection(editor, 'underline'),
    strikeThrough: editor => formatSelection(editor, 'strikeThrough'),
    setFontSize: (editor, size) => formatSelection(editor, 'fontSize', {applyStyle: true, formatProps: {size}}),
    switchDirection: editor => {
        getDeepRange(editor.editable, { splitText: true, select: true, correctTripleClick: true });
        const selection = editor.document.getSelection();
        const selectedTextNodes = [selection.anchorNode, ...getSelectedNodes(editor.editable), selection.focusNode]
            .filter(n => n.nodeType === Node.TEXT_NODE && n.nodeValue.trim().length);

        const changedElements = [];
        const defaultDirection = editor.options.direction;
        const shouldApplyStyle = !isSelectionFormat(editor.editable, 'switchDirection');
        for (const block of new Set(selectedTextNodes.map(textNode => closestBlock(textNode)))) {
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
        const selectedTds = editor.editable.querySelectorAll('td.o_selected_td');
        let coloredTds = [];
        if (selectedTds.length) {
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
        const selectedNodes = getSelectedNodes(editor.editable).filter(node => !closestElement(node, 'table.o_selected_table'));
        const fonts = selectedNodes.flatMap(node => {
            let font = closestElement(node, 'font');
            const children = font && descendants(font);
            if (font && font.nodeName === 'FONT') {
                // Partially selected <font>: split it.
                const selectedChildren = children.filter(child => selectedNodes.includes(child));
                if (selectedChildren.length) {
                    font = splitAroundUntil(selectedChildren, font);
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
        return [...fonts, ...coloredTds];
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
        const [table] = editorCommands.insert(editor, parseHTML(tableHtml));
        setCursorStart(table.querySelector('td'));
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
            newCell.append(document.createElement('br'));
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
        const referenceRowWidths = [...cells].map(cell => cell.style.width || cell.clientWidth + 'px');
        newRow.append(...Array.from(Array(cells.length)).map(() => {
            const td = document.createElement('td');
            td.append(document.createElement('br'));
            return td;
        }));
        referenceRow[beforeOrAfter](newRow);
        newRow.style.height = referenceRowHeight + 'px';
        // Preserve the width of the columns (applied only on the first row).
        if (getRowIndex(newRow) === 0) {
            let columnIndex = 0;
            for (const column of newRow.children) {
                column.style.width = referenceRowWidths[columnIndex];
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
                        node.ouid = undefined; // Allow move out of unbreakable
                        for (const descendant of descendants(node)) {
                            descendant.ouid = undefined; // Allow move out of unbreakable
                        }
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
            block.ouid = undefined; // Allow move out of unbreakable
            for (const descendant of descendants(block)) {
                descendant.ouid = undefined; // Allow move out of unbreakable
            }
            const columnSize = Math.floor(12 / numberOfColumns);
            const columns = [];
            for (let i = 0; i < numberOfColumns; i++) {
                const column = document.createElement('div');
                column.classList.add(`col-lg-${columnSize}`);
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
                    column.classList.add(`col-lg-${columnSize}`);
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
                        node.ouid = undefined; // Allow move out of unbreakable
                        for (const descendant of descendants(node)) {
                            descendant.ouid = undefined; // Allow move out of unbreakable
                        }
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
        const element = closestElement(
            range.startContainer,
            'P, PRE, H1, H2, H3, H4, H5, H6, BLOCKQUOTE',
        );

        if (element && ancestors(element).includes(editor.editable)) {
            element.before(editor.document.createElement('hr'));
        }
    },
};
