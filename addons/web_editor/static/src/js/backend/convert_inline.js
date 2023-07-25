/** @odoo-module alias=web_editor.convertInline */
'use strict';

import { getAdjacentPreviousSiblings, isBlock, rgbToHex, commonParentGet } from '../editor/odoo-editor/src/utils/utils';

//--------------------------------------------------------------------------
// Constants
//--------------------------------------------------------------------------

const RE_COL_MATCH = /(^| )col(-[\w\d]+)*( |$)/;
const RE_COMMAS_OUTSIDE_PARENTHESES = /,(?![^(]*?\))/g;
const RE_OFFSET_MATCH = /(^| )offset(-[\w\d]+)*( |$)/;
const RE_PADDING_MATCH = /[ ]*padding[^;]*;/g;
const RE_PADDING = /([\d.]+)/;
const RE_WHITESPACE = /[\s\u200b]*/;
const SELECTORS_IGNORE = /(^\*$|:hover|:before|:after|:active|:link|::|'|\([^(),]+[,(])/;
// CSS properties relating to font, which Outlook seem to have trouble inheriting.
const FONT_PROPERTIES_TO_INHERIT = [
    'color',
    'font-size',
    'font-family',
    'font-weight',
    'font-style',
    'text-decoration',
    'text-transform',
    'text-align',
];
// Attributes all tables should have in a mailing.
export const TABLE_ATTRIBUTES = {
    cellspacing: 0,
    cellpadding: 0,
    border: 0,
    width: '100%',
    align: 'center',
    role: 'presentation',
};
// Cancel tables default styles.
export const TABLE_STYLES = {
    'border-collapse': 'collapse',
    'text-align': 'inherit',
    'font-size': 'unset',
    'line-height': 'inherit',
};

//--------------------------------------------------------------------------
// Public
//--------------------------------------------------------------------------

/**
 * Convert snippets and mailing bodies to tables.
 *
 * @param {JQuery} $editable
 */
function addTables($editable) {
    const editable = $editable.get(0);
    for (const snippet of editable.querySelectorAll('.o_mail_snippet_general, .o_layout')) {
        // Convert all snippets and the mailing itself into table > tr > td
        const table = _createTable(snippet.attributes);

        const row = document.createElement('tr');
        const col = document.createElement('td');
        row.appendChild(col);
        table.appendChild(row);

        for (const child of [...snippet.childNodes]) {
            col.appendChild(child);
        }
        snippet.before(table);
        snippet.remove();

        // If snippet doesn't have a table as child, wrap its contents in one.
        const childTables = [...col.children].filter(child => child.nodeName === 'TABLE');
        if (!childTables.length) {
            const tableB = _createTable();
            const rowB = document.createElement('tr');
            const colB = document.createElement('td');

            rowB.appendChild(colB);
            tableB.appendChild(rowB);
            for (const child of [...col.childNodes]) {
                colB.appendChild(child);
            }
            col.appendChild(tableB);
        }
    }
}
/**
 * Convert CSS display for attachment link to real image.
 * Without this post process, the display depends on the CSS and the picture
 * does not appear when we use the html without css (to send by email for e.g.)
 *
 * @param {JQuery} $editable
 */
function attachmentThumbnailToLinkImg($editable) {
    const editable = $editable.get(0);
    const links = [...editable.querySelectorAll(`a[href*="/web/content/"][data-mimetype]:empty`)].filter(link => (
        RE_WHITESPACE.test(link.textContent)
    ));
    for (const link of links) {
        const image = document.createElement('img');
        image.setAttribute('src', _getStylePropertyValue(link, 'background-image').replace(/(^url\(['"])|(['"]\)$)/g, ''));
        // Note: will trigger layout thrashing.
        image.setAttribute('height', Math.max(1, _getHeight(link)));
        image.setAttribute('width', Math.max(1, _getWidth(link)));
        link.prepend(image);
    };
}
/**
 * Convert Bootstrap rows and columns to actual tables.
 *
 * Note: Because of the limited support of media queries in emails, this doesn't
 * support the mixing and matching of column options (e.g., "col-4 col-sm-6" and
 * "col col-4" aren't supported).
 *
 * @param {Element} editable
 */
function bootstrapToTable(editable) {
    // First give all rows in columns a separate container parent.
    for (const rowInColumn of [...editable.querySelectorAll('.row')].filter(row => RE_COL_MATCH.test(row.parentElement.className))) {
        const parentColumn = rowInColumn.parentElement;
        const previous = rowInColumn.previousElementSibling;
        if (previous && previous.classList.contains('o_fake_table')) {
            // If a container was already created there, append to it.
            previous.append(rowInColumn);
        } else {
            _wrap(rowInColumn, 'div', 'o_fake_table');
        }
        // Bootstrap rows have negative left and right margins, which are not
        // supported by GMail and Outlook. Add up the padding of the column with
        // the negative margin of the row to get the correct padding.
        const rowStyle = getComputedStyle(rowInColumn);
        const columnStyle = getComputedStyle(parentColumn);
        for (const side of ['left', 'right']) {
            const negativeMargin = +rowStyle[`margin-${side}`].replace('px', '');
            const columnPadding = +columnStyle[`padding-${side}`].replace('px', '');
            if (negativeMargin < 0 && columnPadding >= Math.abs(negativeMargin)) {
                parentColumn.style[`padding-${side}`] = `${columnPadding + negativeMargin}px`;
                rowInColumn.style[`margin-${side}`] = 0;
            }
        }
    }

    // These containers from the mass mailing masonry snippet require full
    // height contents, which is only possible if the table itself has a set
    // height. We also need to restyle it because of the change in structure.
    for(const masonryTopInnerContainer of editable.querySelectorAll('.s_masonry_block > .container')) {
        masonryTopInnerContainer.style.setProperty('height', '100%');
    }
    for (const masonryGrid of editable.querySelectorAll('.o_masonry_grid_container')) {
        masonryGrid.style.setProperty('padding', 0);
        for (const fakeTable of [...masonryGrid.children].filter(c => c.classList.contains('o_fake_table'))) {
            fakeTable.style.setProperty('height', _getHeight(fakeTable) + 'px');
        }
    }
    for (const masonryRow of editable.querySelectorAll('.o_masonry_grid_container > .o_fake_table > .row.h-100')) {
        masonryRow.style.removeProperty('height');
        masonryRow.parentElement.style.setProperty('height', '100%');
    }

    const containers = editable.querySelectorAll('.container, .container-fluid, .o_fake_table');
    // Capture the widths of the containers before manipulating it.
    for (const container of containers) {
        container.setAttribute('o-temp-width', _getWidth(container));
    }
    // Now convert all containers with rows to tables.
    for (const container of [...containers].filter(n => [...n.children].some(c => c.classList.contains('row')))) {
        // The width of the table was stored in a temporary attribute. Fetch it
        // for use in `_applyColspan` and remove the attribute at the end.
        const containerWidth = parseFloat(container.getAttribute('o-temp-width'));

        // TABLE
        const table = _createTable(container.attributes);
        for (const child of [...container.childNodes]) {
            table.append(child);
        }
        table.classList.remove('container', 'container-fluid', 'o_fake_table');
        if (!table.className) {
            table.removeAttribute('class');
        }
        container.before(table);
        container.remove();


        // ROWS
        // First give all siblings of rows a separate row/col parent combo.
        for (const row of [...table.children].filter(child => isBlock(child) && !child.classList.contains('row'))) {
            const newCol = _wrap(row, 'div', 'col-12');
            _wrap(newCol, 'div', 'row');
        }

        for (const bootstrapRow of [...table.children].filter(c => c.classList.contains('row'))) {
            const tr = document.createElement('tr');
            for (const attr of bootstrapRow.attributes) {
                tr.setAttribute(attr.name, attr.value);
            }
            tr.classList.remove('row');
            if (!tr.className) {
                tr.removeAttribute('class');
            }
            for (const child of [...bootstrapRow.childNodes]) {
                tr.append(child);
            }
            bootstrapRow.before(tr);
            bootstrapRow.remove();


            // COLUMNS
            const bootstrapColumns = [...tr.children].filter(column => column.className && column.className.match(RE_COL_MATCH));

            // 1. Replace generic "col" classes with specific "col-n", computed
            //    by sharing the available space between them.
            const flexColumns = bootstrapColumns.filter(column => !/\d/.test(column.className.match(RE_COL_MATCH)[0] || '0'));
            const colTotalSize = bootstrapColumns.map(child => _getColumnSize(child) + _getColumnOffsetSize(child)).reduce((a, b) => a + b, 0);
            const colSize = Math.max(1, Math.round((12 - colTotalSize) / flexColumns.length));
            for (const flexColumn of flexColumns) {
                flexColumn.classList.remove(flexColumn.className.match(RE_COL_MATCH)[0].trim());
                flexColumn.classList.add(`col-${colSize}`);
            }

            // 2. Create and fill up the row(s) with grid(s).
            // Create new, empty columns for column offsets.
            let columnIndex = 0;
            for (const bootstrapColumn of [...bootstrapColumns]) {
                const offsetSize = _getColumnOffsetSize(bootstrapColumn);
                if (offsetSize) {
                    const newColumn = document.createElement('div');
                    newColumn.classList.add(`col-${offsetSize}`);
                    bootstrapColumn.classList.remove(bootstrapColumn.className.match(RE_OFFSET_MATCH)[0].trim());
                    bootstrapColumn.before(newColumn);
                    bootstrapColumns.splice(columnIndex, 0, newColumn);
                    columnIndex++;
                }
                columnIndex++;
            }
            let grid = _createColumnGrid();
            let gridIndex = 0;
            let currentRow = tr.cloneNode();
            tr.after(currentRow);
            let currentCol;
            columnIndex = 0;
            for (const bootstrapColumn of bootstrapColumns) {
                const columnSize = _getColumnSize(bootstrapColumn);
                if (gridIndex + columnSize < 12) {
                    currentCol = grid[gridIndex];
                    _applyColspan(currentCol, columnSize, containerWidth);
                    gridIndex += columnSize;
                    if (columnIndex === bootstrapColumns.length - 1) {
                        // We handled all the columns but there is still space
                        // in the row. Insert the columns and fill the row.
                        _applyColspan(grid[gridIndex], 12 - gridIndex, containerWidth);
                        currentRow.append(...grid.filter(td => td.getAttribute('colspan')));
                    }
                } else if (gridIndex + columnSize === 12) {
                    // Finish the row.
                    currentCol = grid[gridIndex];
                    _applyColspan(currentCol, columnSize, containerWidth);
                    currentRow.append(...grid.filter(td => td.getAttribute('colspan')));
                    if (columnIndex !== bootstrapColumns.length - 1) {
                        // The row was filled before we handled all of its
                        // columns. Create a new one and start again from there.
                        const previousRow = currentRow;
                        currentRow = currentRow.cloneNode();
                        previousRow.after(currentRow);
                        grid = _createColumnGrid();
                        gridIndex = 0;
                    }
                } else {
                    // Fill the row with what was in the grid before it
                    // overflowed.
                    _applyColspan(grid[gridIndex], 12 - gridIndex, containerWidth);
                    currentRow.append(...grid.filter(td => td.getAttribute('colspan')));
                    // Start a new row that starts with the current col.
                    const previousRow = currentRow;
                    currentRow = currentRow.cloneNode();
                    previousRow.after(currentRow);
                    grid = _createColumnGrid();
                    currentCol = grid[0];
                    _applyColspan(currentCol, columnSize, containerWidth);
                    gridIndex = columnSize;
                    if (columnIndex === bootstrapColumns.length - 1 && gridIndex < 12) {
                        // We handled all the columns but there is still space
                        // in the row. Insert the columns and fill the row.
                        _applyColspan(grid[gridIndex], 12 - gridIndex, containerWidth);
                        currentRow.append(...grid.filter(td => td.getAttribute('colspan')));
                    }
                }
                if (currentCol) {
                    for (const attr of bootstrapColumn.attributes) {
                        if (attr.name !== 'colspan') {
                            currentCol.setAttribute(attr.name, attr.value);
                        }
                    }
                    const colMatch = bootstrapColumn.className.match(RE_COL_MATCH);
                    currentCol.classList.remove(colMatch[0].trim());
                    if (!currentCol.className) {
                        currentCol.removeAttribute('class');
                    }
                    for (const child of [...bootstrapColumn.childNodes]) {
                        currentCol.append(child);
                    }
                    // Adapt width to colspan.
                    _applyColspan(currentCol, +currentCol.getAttribute('colspan'), containerWidth);
                }
                columnIndex++;
            }
            tr.remove(); // row was cloned and inserted already
        }
    }
    for (const table of editable.querySelectorAll('table')) {
        table.removeAttribute('o-temp-width');
    }
    // Merge tables in tds into one common table, each in its own row.
    const tds = [...editable.querySelectorAll('td')]
        .filter(td => td.children.length > 1 && [...td.children].every(child => child.nodeName === 'TABLE'))
        .reverse();
    for (const td of tds) {
        const table = _createTable();
        const trs = [...td.children].map(child => _wrap(child, 'td')).map(wrappedChild => _wrap(wrappedChild, 'tr'));
        trs[0].before(table);
        table.append(...trs);
    }
}
/**
 * Convert Bootstrap cards to table structures.
 *
 * @param {Element} editable
 */
function cardToTable(editable) {
    for (const card of editable.querySelectorAll('.card')) {
        const table = _createTable(card.attributes);
        table.style.removeProperty('overflow');
        const cardImgTopSuperRows = [];
        for (const child of [...card.childNodes]) {
            const row = document.createElement('tr');
            const col = document.createElement('td');
            if (isBlock(child)) {
                for (const attr of child.attributes) {
                    col.setAttribute(attr.name, attr.value);
                }
                for (const descendant of [...child.childNodes]) {
                    col.append(descendant);
                }
                child.remove();
            } else if (child.nodeType === Node.TEXT_NODE) {
                if (child.textContent.replace(RE_WHITESPACE, '').length) {
                    col.append(child);
                } else {
                    continue;
                }
            } else {
                col.append(child);
            }
            const subTable = _createTable();
            const superRow = document.createElement('tr');
            const superCol = document.createElement('td');
            row.append(col);
            subTable.append(row);
            superCol.append(subTable);
            superRow.append(superCol);
            table.append(superRow);
            if (child.classList && child.classList.contains('card-img-top')) {
                // Collect .card-img-top superRows to manipulate their heights.
                cardImgTopSuperRows.push(superRow);
            }
        }
        // We expect successive .card-img-top to have the same height so the
        // bodies of the cards are aligned. This achieves that without flexboxes
        // by forcing the height of the smallest card:
        const smallestCardImgRow = Math.min(0, ...cardImgTopSuperRows.map(row => row.clientHeight));
        for (const row of cardImgTopSuperRows) {
            row.style.height = smallestCardImgRow + 'px';
        }
        card.before(table);
        card.remove();
    }
}
/**
 * Convert CSS style to inline style (leave the classes on elements but forces
 * the style they give as inline style).
 *
 * @param {JQuery} $editable
 * @param {Object} cssRules
 */
function classToStyle($editable, cssRules) {
    const editable = $editable.get(0);
    const writes = [];
    const nodeToRules = new Map();
    const rulesToProcess = [];
    for (const rule of cssRules) {
        const nodes = editable.querySelectorAll(rule.selector);
        if (nodes.length) {
            rulesToProcess.push(rule);
        }
        for (const node of nodes) {
            const nodeRules = nodeToRules.get(node);
            if (!nodeRules) {
                nodeToRules.set(node, [rule]);
            } else {
                nodeRules.push(rule);
            }
        }
    }
    _computeStyleAndSpecificityOnRules(rulesToProcess);
    for (const rules of nodeToRules.values()) {
        rules.sort((a, b) => a.specificity - b.specificity);
    }

    for (const node of nodeToRules.keys()) {
        const nodeRules = nodeToRules.get(node);
        const css = nodeRules ? _getMatchedCSSRules(node, nodeRules) : {};
        // Flexbox
        for (const styleName of node.style) {
            if (styleName.includes('flex') || `${node.style[styleName]}`.includes('flex')) {
                writes.push(() => { node.style[styleName] = ''; });
            }
        }

        // Do not apply css that would override inline styles (which are prioritary).
        let style = node.getAttribute('style') || '';
        // Outlook doesn't support inline !important
        style = style.replace(/!important/g,'');
        for (const [key, value] of Object.entries(css)) {
            if (!(new RegExp(`(^|;)\\s*${key}`).test(style))) {
                style = `${key}:${value};${style}`;
            }
        };
        if (_.isEmpty(style)) {
            writes.push(() => { node.removeAttribute('style'); });
        } else {
            writes.push(() => {
                node.setAttribute('style', style);
                if (node.style.width) {
                    node.setAttribute('width', node.style.width.replace('px', '').trim());
                }
            });
        }

        if (node.nodeName === 'IMG') {
            writes.push(() => {
                // Media list images should not have an inline height
                if (node.classList.contains('s_media_list_img')) {
                    node.style.removeProperty('height');
                }
                // Protect aspect ratio when resizing in mobile.
                if (node.style.getPropertyValue('width') === '100%' && node.style.getPropertyValue('object-fit') === '') {
                    node.style.setProperty('object-fit', 'cover');
                }
            });
        }
        // Apple Mail
        if (node.nodeName === 'TD' && !node.childNodes.length) {
            // Append non-breaking spaces to empty table cells.
            writes.push(() => { node.appendChild(document.createTextNode('\u00A0')); });
        }
        // Outlook
        if (node.nodeName === 'A' && node.classList.contains('btn') && !node.classList.contains('btn-link') && !node.children.length) {
            writes.push(() => {
                node.before(_createMso(`<table align="center" border="0"
                    role="presentation" cellpadding="0" cellspacing="0"
                    style="border-radius: 6px; border-collapse: separate !important;">
                        <tbody>
                            <tr>
                                <td style="${node.style.cssText.replace(RE_PADDING_MATCH, '').replaceAll('"', '&quot;')}" ${
                                    node.parentElement.style.textAlign === 'center' ? 'align="center" ' : ''
                                }bgcolor="${rgbToHex(node.style.backgroundColor)}">
                    `));
                node.after(_createMso(`</td>
                        </tr>
                    </tbody>
                </table>`));
            });
        } else if (node.nodeName === 'IMG' && node.classList.contains('mx-auto') && node.classList.contains('d-block')) {
            writes.push(() => { _wrap(node, 'p', 'o_outlook_hack', 'text-align:center;margin:0'); });
        }

        // Compute dynamic styles (var, calc).
        writes.push(() => {
            let computedStyle;
            for (const styleName of node.style) {
                const styleValue = node.style.getPropertyValue(styleName);
                if (styleValue.includes('var(') || styleValue.includes('calc(')) {
                    computedStyle = computedStyle || getComputedStyle(node);
                    const prop = styleValue.includes('var(') ? styleValue.replace(/var\((.*)\)/, '$1') : styleName;
                    const value = computedStyle.getPropertyValue(prop) || computedStyle.getPropertyValue(styleName);
                    node.style.setProperty(styleName, value);
                }
            }
        });

        // Fix inheritance of font properties on Outlook.
        writes.push(() => {
            const propsToConvert = FONT_PROPERTIES_TO_INHERIT.filter(prop => node.style[prop] === 'inherit');
            if (propsToConvert.length) {
                const computedStyle = getComputedStyle(node);
                for (const prop of propsToConvert) {
                    node.style.setProperty(prop, computedStyle[prop]);
                }
            }
        });
    };
    writes.forEach(fn => fn());
}
/**
 * Add styles to all table rows and columns, that are necessary for them to be
 * responsive. This only works if columns have a max-width so the styles are
 * only applied to columns where that is the case.
 *
 * @param {Element} editable
 */
function enforceTablesResponsivity(editable) {
    // Trying this: https://www.litmus.com/blog/mobile-responsive-email-stacking/
    const trs = [...editable.querySelectorAll('.o_mail_wrapper tr')]
        .filter(tr => [...tr.children].some(td => td.classList.contains('o_converted_col')))
        .reverse();
    for (const tr of trs) {
        const commonTable = _createTable();
        commonTable.style.height = '100%';
        const commonTr = document.createElement('tr');
        const commonTd = document.createElement('td');
        commonTr.appendChild(commonTd);
        commonTable.appendChild(commonTr);
        const tds = [...tr.children].filter(child => child.nodeName === 'TD');
        let index = 0;
        for (const td of tds) {
            const width = td.style.maxWidth;
            const div = document.createElement('div');
            div.style.display = 'inline-block';
            div.style.verticalAlign = 'top';
            div.classList.add('o_stacking_wrapper');
            commonTd.appendChild(div);
            const newTable = _createTable();
            newTable.style.width = width;
            newTable.classList.add('o_stacking_wrapper');
            div.appendChild(newTable);
            const newTr = document.createElement('tr');
            newTable.appendChild(newTr);
            newTr.appendChild(td);
            td.style.width = '100%';
            td.removeAttribute('width');
            if (index === 0) {
                div.before(_createMso(`
                    <table cellpadding="0" cellspacing="0" border="0" role="presentation" style="width: 100%;">
                        <tr>
                            <td valign="top" style="width: ${width};">`));
            } else {
                div.before(_createMso(`</td><td valign="top" style="width: ${width};">`));
            }
            if (index === tds.length - 1) {
                div.after(_createMso(`</td></tr></table>`));
            }
            index++;
        }
        const topTd = document.createElement('td');
        topTd.appendChild(commonTable);
        tr.prepend(topTd);
    }
}
// Masonry has crazy nested tables that require some extra treatment.
function handleMasonry(editable) {
    const masonryTrs = editable.querySelectorAll('.s_masonry_block tr');
    for (const tr of masonryTrs) {
        const height = _getHeight(tr);
        const tds = [...tr.children].filter(child => child.nodeName === 'TD');
        const tdsWithTable = tds.filter(td => [...td.children].some(child => child.nodeName === 'TABLE'));
        if (tdsWithTable.length) {
            // TODO: this seems a duplicate of the other o_desktop_h100 set below.
            // Set the cells' heights to fill their parents.
            for (const tdWithTable of tdsWithTable) {
                tdWithTable.classList.add('o_desktop_h100');
                tdWithTable.style.setProperty('height', '100%');
            }
            // We also have to set the same height on the cells' sibling TDs.
            tds.forEach(td => td.style.setProperty('height', height + 'px'));
        }
        // Sometimes Masonry declares rows with a height of 100% but with
        // columns that overfit the grid. In these cases, we split the rows into
        // multiple rows so we need to adapt their heights for them to be
        // divided equally.
        const trSiblings = [...tr.parentElement.children].filter(child => child.nodeName === 'TR');
        if (trSiblings.length > 1 && (tr.classList.contains('h-100') || tr.style.getPropertyValue('height') === '100%')) {
            tr.style.setProperty('height', `${_getHeight(tr.parentElement) / trSiblings.length}px`);
        }
    }
    for (const tr of masonryTrs) {
        const height = tr.style.height.includes('px') ? parseFloat(tr.style.height.replace('px', '').trim()) : _getHeight(tr);
        tr.closest('table').classList.add('o_desktop_h100');
        tr.classList.add('o_desktop_h100');
        for (const td of [...tr.children].filter(child => child.nodeName === 'TD')) {
            td.classList.add('o_desktop_h100');
            td.style.setProperty('height', '100%');
            const childrenNames = [...td.children].map(child => child.nodeName);
            if (!childrenNames.includes('TABLE')) {
                // Hack that makes vertical-align possible within an inline-block.
                const wrapper = document.createElement('div');
                wrapper.style.setProperty('display', 'inline-block');
                wrapper.style.setProperty('width', '100%');
                // Transfer color to wrapper for Outlook on MacOS/iOS.
                const tdStyle = getComputedStyle(td);
                wrapper.style.setProperty('color', tdStyle.color);
                const firstNonCommentChild = [...td.childNodes].find(child => child.nodeType !== Node.COMMENT_NODE);
                let anchor;
                if (firstNonCommentChild) {
                    anchor = getAdjacentPreviousSiblings(firstNonCommentChild)
                        .filter(sib => sib.nodeType !== Node.TEXT_NODE)
                        .shift();
                }
                for (const child of [...td.childNodes].filter(child => child.nodeType !== Node.COMMENT_NODE)) {
                    wrapper.append(child);
                }
                anchor ? anchor.after(wrapper) : td.append(wrapper);
                const centeringSpan = document.createElement('span');
                centeringSpan.style.setProperty('height', '100%');
                centeringSpan.style.setProperty('display', 'inline-block');
                centeringSpan.style.setProperty('vertical-align', 'middle');
                td.prepend(centeringSpan);
                // Height on cells should be applied in pixels.
                if (td.style.height.includes('%')) {
                    const newHeight = height * parseFloat(td.style.height.replace('%').trim()) / 100;
                    td.style.setProperty('height', newHeight + 'px');
                    // Spread height down for responsivity
                    td.style.setProperty('max-height', newHeight + 'px');
                    wrapper.style.setProperty('max-height', newHeight + 'px');
                    if (wrapper.childElementCount === 1 && wrapper.firstElementChild.nodeName === 'IMG' && wrapper.firstElementChild.style.height === '100%') {
                        wrapper.firstElementChild.style.setProperty('max-height', newHeight + 'px');
                    }
                }
            }
        }
    }
}
/**
 * Modify the styles of images so they are responsive.
 *
 * @param {Element} editable
 */
function enforceImagesResponsivity(editable) {
    // Images with 100% height in cells should preserve that height and the
    // height of the row should be applied to the cell.
    for (const image of editable.querySelectorAll('td > img')) {
        const td = image.parentElement;
        if (td.childElementCount === 1 && (image.classList.contains('h-100') || _getStylePropertyValue(image, 'height') === '100%')) {
            td.style.setProperty('height', _getHeight(td.parentElement) + 'px');
            image.style.setProperty('height', '100%');
        }
    }
    // Remove the height attribute in card images so they can resize
    // responsively, but leave it for Outlook.
    for (const image of editable.querySelectorAll('img[width="100%"][height]')) {
        image.before(_createMso(image.outerHTML));
        image.classList.add('mso-hide');
        image.removeAttribute('height');
    }
}
/**
 * Convert the contents of an editable area (as a JQuery element) into content
 * that is widely compatible with email clients. If no CSS Rules are given, they
 * will be computed for the editable element's owner document.
 *
 * @param {JQuery} $editable
 * @param {Object[]} [cssRules] Array<{selector: string;
 *                                   style: {[styleName]: string};
 *                                   specificity: number;}>
 * @param {JQuery} [$iframe] the iframe containing the editable, if any
 */
async function toInline($editable, cssRules, $iframe) {
    $editable.removeClass('odoo-editor-editable');
    const editable = $editable.get(0);
    const iframe = $iframe && $iframe.get(0);
    const wysiwyg = $editable.data('wysiwyg');
    const doc = editable.ownerDocument;
    cssRules = cssRules || wysiwyg && wysiwyg._rulesCache;
    if (!cssRules) {
        cssRules = getCSSRules(doc);
        if (wysiwyg) {
            wysiwyg._rulesCache = cssRules;
        }
    }

    // If the editable is not visible, we need to make it visible in order to
    // retrieve image/icon dimensions. This iterates over ancestors to make them
    // visible again. We then restore it at the end of this function.
    const displaysToRestore = [];
    if (_isHidden(editable)) {
        let ancestor = editable;
        while (ancestor && ancestor.nodeName !== 'html' && _isHidden(ancestor)) {
            if (_getStylePropertyValue(ancestor, 'display') === 'none') {
                displaysToRestore.push([ancestor, ancestor.style.display]);
                ancestor.style.setProperty('display', 'block');
            }
            ancestor = ancestor.parentElement;
            if ((!ancestor || ancestor.nodeName === 'HTML') && iframe) {
                ancestor = iframe;
            }
        }
    }
    // Fix card-img-top heights (must happen before we transform everything).
    for (const imgTop of editable.querySelectorAll('.card-img-top')) {
        imgTop.style.setProperty('height', _getHeight(imgTop) + 'px');
    }

    attachmentThumbnailToLinkImg($editable);
    fontToImg($editable);
    await svgToPng($editable);

    // Fix img-fluid for Outlook.
    for (const image of editable.querySelectorAll('img.img-fluid')) {
        const width = _getWidth(image);
        const clone = image.cloneNode();
        clone.setAttribute('width', width);
        clone.style.setProperty('width', width + 'px');
        clone.style.removeProperty('max-width');
        image.before(_createMso(clone.outerHTML));
        _hideForOutlook(image);
    }

    classToStyle($editable, cssRules);
    bootstrapToTable(editable);
    cardToTable(editable);
    listGroupToTable(editable);
    addTables($editable);
    handleMasonry(editable);
    const rootFontSizeProperty = getComputedStyle(editable.ownerDocument.documentElement).fontSize;
    const rootFontSize = parseFloat(rootFontSizeProperty.replace(/[^\d\.]/g, ''));
    normalizeRem($editable, rootFontSize);
    enforceImagesResponsivity(editable);
    enforceTablesResponsivity(editable);
    flattenBackgroundImages(editable);
    formatTables($editable);
    normalizeColors($editable);
    responsiveToStaticForOutlook(editable);
    // Fix Outlook image rendering bug.
    for (const attributeName of ['width', 'height']) {
        const images = editable.querySelectorAll('img');
        for (const image of images) {
            if (image.style[attributeName] !== 'auto') {
                const value = image.getAttribute(attributeName) ||
                    (attributeName === 'height' && image.offsetHeight) ||
                    (attributeName === 'width' ? _getWidth(image) : _getHeight(image));
                if (value) {
                    image.setAttribute(attributeName, value);
                    image.style.setProperty(attributeName, value + 'px');
                }
            }
        };
    };
    // Fix mx-auto on images in table cells.
    for (const centeredImage of editable.querySelectorAll('td > img.mx-auto')) {
        if (centeredImage.parentElement.children.length === 1) {
            centeredImage.parentElement.style.setProperty('text-align', 'center');
        }
    }

    // Remove contenteditable attributes
    [editable, ...editable.querySelectorAll('[contenteditable]')].forEach(node => node.removeAttribute('contenteditable'));

    // Hide replaced cells on Outlook
    editable.querySelectorAll('.mso-hide').forEach(_hideForOutlook);

    // Replace double quotes in font-family styles with simple quotes (and
    // simply remove these styles from images).
    editable.querySelectorAll('[style*=font-family]').forEach(n => (
        n.nodeName === 'IMG'
            ? n.style.removeProperty('font-family')
            : n.setAttribute('style', n.getAttribute('style').replaceAll('"', '\''))
    ));

    // Styles were applied inline, we don't need a style element anymore.
    $editable.find('style').remove();

    editable.querySelectorAll('.o_converted_col').forEach(node => node.classList.remove('o_converted_col'));

    for (const [node, displayValue] of displaysToRestore) {
        node.style.setProperty('display', displayValue);
    }
    $editable.addClass('odoo-editor-editable');
}
/**
 * Take all elements with a `background-image` style and convert them to `vml`
 * for Outlook.
 *
 * @param {Element} editable
 */
function flattenBackgroundImages(editable) {
    const backgroundImages = [...editable.querySelectorAll('*[style*=background-image]')]
        .filter(el => !el.closest('.mso-hide'))
        .reverse();
    for (const backgroundImage of backgroundImages) {
        const vml = _backgroundImageToVml(backgroundImage);
        if (vml) {
            // Put the Outlook version after the original one in an mso conditional.
            backgroundImage.after(_createMso(vml));
            // Hide the original element for Outlook.
            backgroundImage.classList.add('mso-hide');
        }
    }
}
/**
 * Convert font icons to images.
 *
 * @param {JQuery} $editable - the element in which the font icons have to be
 *                           converted to images
 */
function fontToImg($editable) {
    const editable = $editable.get(0);
    const fonts = odoo.__DEBUG__.services["wysiwyg.fonts"];

    for (const font of editable.querySelectorAll('.fa')) {
        let icon, content;
        fonts.fontIcons.find(fontIcon => {
            return fonts.getCssSelectors(fontIcon.parser).find(data => {
                if (font.matches(data.selector.replace(/::?before/g, ''))) {
                    icon = data.names[0].split('-').shift();
                    content = data.css.match(/content:\s*['"]?(.)['"]?/)[1];
                    return true;
                }
            });
        });
        if (content) {
            const color = _getStylePropertyValue(font, 'color').replace(/\s/g, '');
            let backgroundColoredElement = font;
            let bg, isTransparent;
            do {
                bg = _getStylePropertyValue(backgroundColoredElement, 'background-color').replace(/\s/g, '');
                isTransparent = bg === 'transparent' || bg === 'rgba(0,0,0,0)';
                backgroundColoredElement = backgroundColoredElement.parentElement;
            } while (isTransparent && backgroundColoredElement);
            if (bg === 'rgba(0,0,0,0)' && isTransparent) {
                // default on white rather than black background since opacity
                // is not supported.
                bg = 'rgb(255,255,255)';
            }
            const style = font.getAttribute('style');
            const width = _getWidth(font);
            const height = _getHeight(font);
            const lineHeight = _getStylePropertyValue(font, 'line-height');
            // Compute the padding.
            // First get the dimensions of the icon itself (::before)
            font.style.setProperty('height', 'fit-content');
            font.style.setProperty('width', 'fit-content');
            font.style.setProperty('line-height', 'normal');
            const intrinsicWidth = _getWidth(font);
            const intrinsicHeight = _getHeight(font);
            const hPadding = width && intrinsicWidth && (width - intrinsicWidth) / 2;
            const vPadding = height && intrinsicHeight && (height - intrinsicHeight) / 2;
            let padding = '';
            if (hPadding || vPadding) {
                padding = vPadding ? vPadding + 'px ' : '0 ';
                padding += hPadding ? hPadding + 'px' : '0';
            }
            const image = document.createElement('img');
            image.setAttribute('width', intrinsicWidth);
            image.setAttribute('height', intrinsicHeight);
            image.setAttribute('src', `/web_editor/font_to_img/${content.charCodeAt(0)}/${encodeURIComponent(color)}/${encodeURIComponent(bg)}/${Math.max(1, Math.round(intrinsicWidth))}x${Math.max(1, Math.round(intrinsicHeight))}`);
            image.setAttribute('data-class', font.getAttribute('class'));
            image.setAttribute('data-style', style);
            image.setAttribute('style', style);
            image.style.setProperty('box-sizing', 'border-box'); // keep the fontawesome's dimensions
            image.style.setProperty('line-height', lineHeight);
            image.style.setProperty('width', intrinsicWidth + 'px');
            image.style.setProperty('height', intrinsicHeight + 'px');
            image.style.setProperty('vertical-align', 'unset'); // undo Bootstrap's default (middle).
            if (!padding) {
                image.style.setProperty('margin', _getStylePropertyValue(font, 'margin'));
            }
            // For rounded images, apply the rounded border to a wrapper, make
            // sure it doesn't get applied to the image itself so the image
            // doesn't get cropped in the process.
            const wrapper = document.createElement('span');
            wrapper.style.setProperty('display', 'inline-block');
            wrapper.append(image);
            font.before(wrapper);
            if (font.classList.contains('mx-auto')) {
                wrapper.parentElement.style.textAlign = 'center';
            }
            font.remove();
            wrapper.style.setProperty('padding', padding);
            const wrapperWidth = width + ['left', 'right'].reduce((sum, side) => (
                sum + (+_getStylePropertyValue(image, `margin-${side}`).replace('px', '') || 0)
            ), 0);
            wrapper.style.setProperty('width', wrapperWidth + 'px');
            wrapper.style.setProperty('height', height + 'px');
            wrapper.style.setProperty('vertical-align', 'text-bottom');
            wrapper.style.setProperty('background-color', image.style.backgroundColor);
            wrapper.setAttribute('class',
                'oe_unbreakable ' + // prevent sanitize from grouping image wrappers
                font.getAttribute('class').replace(new RegExp('(^|\\s+)' + icon + '(-[^\\s]+)?', 'gi'), '') // remove inline font-awsome style
            );
        } else {
            font.remove();
        }
    }
}
/**
 * Format table styles so they display well in most mail clients. This implies
 * moving table paddings to its cells, adding tbody (with canceled styles) where
 * needed, and adding pixel heights to parents of elements with percent heights.
 *
 * @param {JQuery} $editable
 */
function formatTables($editable) {
    const editable = $editable.get(0);
    const writes = [];
    for (const table of editable.querySelectorAll('table.o_mail_snippet_general, .o_mail_snippet_general table')) {
        const tablePaddingTop = parseFloat(_getStylePropertyValue(table, 'padding-top').match(RE_PADDING)[1]);
        const tablePaddingRight = parseFloat(_getStylePropertyValue(table, 'padding-right').match(RE_PADDING)[1]);
        const tablePaddingBottom = parseFloat(_getStylePropertyValue(table, 'padding-bottom').match(RE_PADDING)[1]);
        const tablePaddingLeft = parseFloat(_getStylePropertyValue(table, 'padding-left').match(RE_PADDING)[1]);
        const rows = [...table.querySelectorAll('tr')].filter(tr => tr.closest('table') === table);
        const columns = [...table.querySelectorAll('td')].filter(td => td.closest('table') === table);
        for (const column of columns) {
            const columnsInRow = [...column.closest('tr').querySelectorAll('td')].filter(td => td.closest('table') === table);
            const columnIndex = columnsInRow.findIndex(col => col === column);
            const rowIndex = rows.findIndex(row => row === column.closest('tr'));

            if (!rowIndex) {
                const match = _getStylePropertyValue(column, 'padding-top').match(RE_PADDING);
                const columnPaddingTop = match ? parseFloat(match[1]) : 0;
                writes.push(() => {column.style['padding-top'] = `${columnPaddingTop + tablePaddingTop}px`; });
            }
            if (columnIndex === columnsInRow.length - 1) {
                const match = _getStylePropertyValue(column, 'padding-right').match(RE_PADDING);
                const columnPaddingRight = match ? parseFloat(match[1]) : 0;
                writes.push(() => {column.style['padding-right'] = `${columnPaddingRight + tablePaddingRight}px`; });
            }
            if (rowIndex === rows.length - 1) {
                const match = _getStylePropertyValue(column, 'padding-bottom').match(RE_PADDING);
                const columnPaddingBottom = match ? parseFloat(match[1]) : 0;
                writes.push(() => {column.style['padding-bottom'] = `${columnPaddingBottom + tablePaddingBottom}px`; });
            }
            if (!columnIndex) {
                const match = _getStylePropertyValue(column, 'padding-left').match(RE_PADDING);
                const columnPaddingLeft = match ? parseFloat(match[1]) : 0;
                writes.push(() => {column.style['padding-left'] = `${columnPaddingLeft + tablePaddingLeft}px`; });
            }
        }
        writes.push(() => { table.style.removeProperty('padding'); });
    }
    writes.forEach((fn) => fn());
    // Ensure a tbody in every table and cancel its default style.
    for (const table of [...editable.querySelectorAll('table')].filter(n => ![...n.children].some(c => c.nodeName === 'TBODY'))) {
        const contents = [...table.childNodes];
        const tbody = document.createElement('tbody');
        tbody.style.setProperty('vertical-align', 'top');
        table.prepend(tbody);
        tbody.append(...contents);
    }
    // Children will only take 100% height if the parent has a height property.
    for (const node of [...editable.querySelectorAll('*')].filter(n => (
        n.style && n.style.getPropertyValue('height') === '100%' && (
            !n.parentElement.style.getPropertyValue('height') ||
            n.parentElement.style.getPropertyValue('height').includes('%'))
    ))) {
        let parent = node.parentElement;
        let height = parent.style.getPropertyValue('height');
        while (parent && height && height.includes('%')) {
            parent = parent.parentElement;
            height = parent.style.getPropertyValue('height');
        }
        if (parent) {
            parent.style.setProperty('height', $(parent).height());
        }
    }
    // Align self and justify content don't work on table cells.
    for (const cell of editable.querySelectorAll('td')) {
        const alignSelf = cell.style.alignSelf;
        const justifyContent = cell.style.justifyContent;
        if (alignSelf === 'start' || justifyContent === 'start' || justifyContent === 'flex-start') {
            cell.style.verticalAlign = 'top';
        } else if (alignSelf === 'center' || justifyContent === 'center') {
            const parentCell = cell.parentElement.closest('td');
            const parentTable = cell.closest('table');
            if (parentCell) {
                parentTable.style.height = _getHeight(parentCell) + 'px';
            }
            cell.style.verticalAlign = 'middle';
        } else if (alignSelf === 'end' || justifyContent === 'end' || justifyContent === 'flex-end') {
            cell.style.verticalAlign = 'bottom';
        }
    }
    // Align items doesn't work on table rows.
    for (const row of editable.querySelectorAll('tr')) {
        const alignItems = row.style.alignItems;
        if (alignItems === 'flex-start') {
            row.style.verticalAlign = 'top';
        } else if (alignItems === 'center') {
            row.style.verticalAlign = 'middle';
        } else if (alignItems === 'flex-end' || alignItems === 'baseline') {
            row.style.verticalAlign = 'bottom';
        } else if (alignItems === 'stretch') {
            const columns = [...row.querySelectorAll('td.o_converted_col')];
            if (columns.length > 1) {
                const commonAncestor = commonParentGet(columns[0], columns[1]);
                const biggestHeight = commonAncestor.clientHeight;
                for (const column of columns) {
                    column.style.height = biggestHeight + 'px';
                }
            }
        }
    }
    // Tables don't properly inherit certain styles from their ancestors in Outlook.
    for (const table of editable.querySelectorAll('table')) {
        const propsToConvert = FONT_PROPERTIES_TO_INHERIT.filter(prop => table.style[prop] === 'inherit' || !table.style[prop]);
        if (propsToConvert.length) {
            for (const prop of propsToConvert) {
                let ancestor = table;
                while (ancestor && (!ancestor.style[prop] || ancestor.style[prop] === 'inherit')) {
                    ancestor = ancestor.parentElement;
                }
                if (ancestor) {
                    table.style.setProperty(prop, ancestor.style[prop]);
                }
            }
        }
    }
}
/**
 * Parse through the given document's stylesheets, preprocess(*) them and return
 * the result as an array of objects, each containing a selector string , a
 * style object and a specificity number. Preprocessing involves grouping
 * whatever rules can be grouped together and precomputing their specificity so
 * as to sort them appropriately.
 *
 * @param {Document} doc
 * @returns {Object[]} Array<{selector: string;
 *                            style: {[styleName]: string};
 *                            specificity: number;}>
 */
function getCSSRules(doc) {
    const cssRules = [];
    for (const sheet of doc.styleSheets) {
        // try...catch because browser may not able to enumerate rules for cross-domain sheets
        let rules;
        try {
            rules = sheet.rules || sheet.cssRules;
        } catch (e) {
            console.log("Can't read the css rules of: " + sheet.href, e);
            continue;
        }
        for (const rule of (rules || [])) {
            const subRules = [rule];
            const conditionText = rule.conditionText;
            const minWidthMatch = conditionText && conditionText.match(/\(min-width *: *(\d+)/);
            const minWidth = minWidthMatch && +(minWidthMatch[1] || '0');
            if (minWidth && minWidth >= 992) {
                // Large min-width media queries should be included.
                // eg., .container has a default max-width for all screens.
                let mediaRules;
                try {
                    mediaRules = rule.rules || rule.cssRules;
                    subRules.push(...mediaRules);
                } catch (e) {
                    console.log(`Can't read the css rules of: ${sheet.href} (${conditionText})`, e);
                }
            }
            for (const subRule of subRules) {
                const selectorText = subRule.selectorText || '';
                // Split selectors, making sure not to split at commas in parentheses.
                for (const selector of selectorText.split(RE_COMMAS_OUTSIDE_PARENTHESES)) {
                    if (selector && !SELECTORS_IGNORE.test(selector)) {
                        cssRules.push({ selector: selector.trim(), rawRule: subRule });
                        if (selector === 'body') {
                            // The top element of a mailing has the class
                            // 'o_layout'. Give it the body's styles so they can
                            // trickle down.
                            cssRules.push({ selector: '.o_layout', rawRule: subRule, specificity: 1 });
                        }
                    }
                }
            }
        }
    }

    return cssRules;
}
/**
 * Convert Bootstrap list groups and their items to table structures.
 *
 * @param {Element} editable
 */
function listGroupToTable(editable) {
    for (const listGroup of editable.querySelectorAll('.list-group')) {
        let table;
        if (listGroup.querySelectorAll('.list-group-item').length) {
            table = _createTable(listGroup.attributes);
        } else {
            table = listGroup.cloneNode();
            for (const attr of listGroup.attributes) {
                table.setAttribute(attr.name, attr.value);
            }
        }
        for (const child of [...listGroup.childNodes]) {
            if (child.classList && child.classList.contains('list-group-item')) {
                // List groups are <ul>s that render like tables. Their
                // li.list-group-item children should translate to tr > td.
                const row = document.createElement('tr');
                const col = document.createElement('td');
                for (const attr of child.attributes) {
                    col.setAttribute(attr.name, attr.value);
                }
                col.append(...child.childNodes);
                col.classList.remove('list-group-item');
                if (!col.className) {
                    col.removeAttribute('class');
                }
                row.append(col);
                table.append(row);
                child.remove();
            } else if (child.nodeName === 'LI') {
                table.append(...child.childNodes);
            } else {
                table.append(child);
            }
        }
        table.classList.remove('list-group');
        if (!table.className) {
            table.removeAttribute('class');
        }
        if (listGroup.nodeName === 'TD') {
            listGroup.append(table);
            listGroup.classList.remove('list-group');
            if (!listGroup.className) {
                listGroup.removeAttribute('class');
            }
        } else {
            listGroup.before(table);
            listGroup.remove();
        }
    }
}
/**
 * Convert all styles containing rgb colors to hexadecimal colors.
 * Note: ignores rgba colors, which are not supported in Microsoft Outlook.
 *
 * @param {JQuery} $editable
 */
function normalizeColors($editable) {
    const editable = $editable.get(0);
    for (const node of editable.querySelectorAll('[style*="rgb"]')) {
        const rgbaMatch = node.getAttribute('style').match(/rgba?\(([\d\.]+\s*,?\s*){3,4}\)/g);
        for (const rgb of rgbaMatch || []) {
            node.setAttribute('style', node.getAttribute('style').replace(rgb, rgbToHex(rgb, node)));
        }
    }
}
/**
 * Convert all css values that use the rem unit to px.
 *
 * @param {JQuery} $editable
 * @param {Number} rootFontSize=16 The font size of the root element, in pixels
 */
function normalizeRem($editable, rootFontSize=16) {
    const editable = $editable.get(0);
    for (const node of editable.querySelectorAll('[style*="rem"]')) {
        const remMatch = node.getAttribute('style').match(/[\d\.]+\s*rem/g);
        for (const rem of remMatch || []) {
            const remValue = parseFloat(rem.replace(/[^\d\.]/g, ''));
            const pxValue = Math.round(remValue * rootFontSize * 100) / 100;
            node.setAttribute('style', node.getAttribute('style').replace(rem, pxValue + 'px'));
        }
    }
}

/**
 * This replaces column html with a dumbed down, Outlook-compliant version of
 * them just for Outlook so while not responsive, these columns still display OK
 * on Outlook.
 *
 * @param {Element} editable
 */
 function responsiveToStaticForOutlook(editable) {
    // Replace the responsive tables with static ones for Outlook
    for (const td of editable.querySelectorAll('td.o_converted_col:not(.mso-hide)')) {
        const tdStyle = td.getAttribute('style') || '';
        const msoAttributes = [...td.attributes].filter(attr => attr.name !== 'style' && attr.name !== 'width');
        const msoWidth = td.style.getPropertyValue('max-width');
        const msoStyles = tdStyle.replace(/(^| |max-)width:[^;]*;\s*/g, '');
        const outlookTd = document.createElement('td');
        for (const attribute of msoAttributes) {
            outlookTd.setAttribute(attribute.name, td.getAttribute(attribute.name));
        }
        if (msoWidth) {
            outlookTd.setAttribute('width', ('' + msoWidth).replace('px', '').trim());
            outlookTd.setAttribute('style', `${msoStyles}width: ${msoWidth};`);
        } else {
            outlookTd.setAttribute('style', msoStyles);
        }
        if (td.closest('.s_masonry_block')) {
            outlookTd.style.padding = 0; // Not sure why this is needed.
        }
        // Outlook doesn't support left/right padding on images. When the image
        // is the only child of its parent, apply said padding to the parent.
        if (td.children.length === 1 && td.firstElementChild.nodeName === 'IMG') {
            const tdComputedStyle = getComputedStyle(td);
            for (const side of ['left', 'right']) {
                if (td.firstElementChild.style.width === '100%') {
                    const prop = `padding-${side}`;
                    const imagePadding = +td.firstElementChild.style[prop].replace('px', '');
                    if (imagePadding > 0) {
                        const tdPadding = +tdComputedStyle[prop].replace('px', '') || 0;
                        outlookTd.style[prop] = tdPadding + imagePadding + 'px';
                    }
                }
            }
        }
        // The opening tag of `outlookTd` is for Outlook.
        td.before(_createMso(outlookTd.outerHTML.replace('</td>', '')));
        // The opening tag of `td` is for the others.
        _hideForOutlook(td, 'opening');
    }
}
/**
 * Convert images of type svg to png.
 *
 * @param {JQuery} $editable
 */
async function svgToPng($editable) {
    for (const svg of $editable.find('img[src*=".svg"]')) {
        // Make sure the svg is loaded before we convert it.
        await new Promise(resolve => {
            svg.onload = () => resolve();
            if (svg.complete) {
                resolve();
            }
        });
        const image = document.createElement('img');
        const canvas = document.createElement('CANVAS');
        const width = _getWidth(svg);
        const height = _getHeight(svg);

        canvas.setAttribute('width', width);
        canvas.setAttribute('height', height);
        canvas.getContext('2d').drawImage(svg, 0, 0, width, height);

        for (const attribute of svg.attributes) {
            image.setAttribute(attribute.name, attribute.value);
        }

        image.setAttribute('src', canvas.toDataURL('png'));
        image.setAttribute('width', width);
        image.setAttribute('height', height);

        svg.before(image);
        svg.remove();
    }
}

//--------------------------------------------------------------------------
// Private
//--------------------------------------------------------------------------

/**
 * Take an element and apply a colspan to it. In this context, this implies to
 * also apply a width to it, that corresponds to the colspan.
 *
 * @param {Element} element
 * @param {number} colspan
 * @param {number} tableWidth
 */
function _applyColspan(element, colspan, tableWidth) {
    element.setAttribute('colspan', colspan);
    const widthPercentage = +element.getAttribute('colspan') / 12;
    // Round to 2 decimal places.
    const width = Math.round(tableWidth * widthPercentage * 100) / 100;
    element.style.setProperty('max-width', width + 'px');
    element.classList.add('o_converted_col');
}
/**
 * Take an element with a background image and return a string containing the
 * VML code to display the same image properly in Outlook, with its contents
 * inside.
 * Note that this assumes:
 *   - background-size: cover,
 *   - background-repeat: no-repeat,
 *   - size 100%
 *   - content is centered x/y
 * TODO: centering span probably not needed with `v-text-anchor:middle` present.
 *
 * @param {Element} backgroundImage
 * @returns {string}
 */
function _backgroundImageToVml(backgroundImage) {
    const matches = backgroundImage.style.backgroundImage.match(/url\("?(.+?)"?\)/);
    const url = matches && matches[1];
    if (url) {
        // Create the outer structure.
        const clone = backgroundImage.cloneNode(true);
        const div = document.createElement('div');
        div.replaceChildren(...clone.childNodes);
        [['fontSize', 0], ['height', '100%'], ['width', '100%']].forEach(([k, v]) => div.style[k] = v);
        const vmlContent = document.createElement('div');
        vmlContent.append(div);

        // Preserve important inherited properties without ancestor context.
        const style = getComputedStyle(backgroundImage);
        for (const prop of FONT_PROPERTIES_TO_INHERIT) {
            div.style[prop] = backgroundImage.style[prop] || style[prop];
        }
        [...div.children].forEach(child => child.style.setProperty('font-size', child.style.fontSize || style.fontSize));

        // Prepare the top element for hosting the VML image.
        for (const prop of ['background', 'background-image', 'background-repeat', 'background-size']) {
            clone.style.removeProperty(prop);
        }
        clone.style.padding = 0;
        clone.className = clone.className.replace(/p[bt]\d+/g, ''); // Remove padding classes.
        clone.setAttribute('background', url);
        clone.setAttribute('valign', 'middle');

        // Create the VML structure, with the content of the original element inside.
        const [width, height] = [_getWidth(backgroundImage), _getHeight(backgroundImage)];
        const vml = `<v:image xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" ` +
            `style="border: 0; display: inline-block; width: ${width}px; height: ${height}px;" src="${url}"/>
        <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" ` +
            `style="border: 0; display: inline-block; position: absolute; width:${width}px; height:${height}px; v-text-anchor:middle;">
            <v:fill opacity="0%" color="#000000"/>
            <v:textbox inset="0,0,0,0">
                <table border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="${width}" align="center" style="text-align: center;">${vmlContent.outerHTML}</td>
                    </tr>
                </table>
            </v:textbox>
        </v:rect>`;

        // Wrap the VML in the original opening and closing tags.
        return `${clone.outerHTML.replace(/<\/[\w-]+>[\s\n]*$/, '')}${vml}</${clone.nodeName.toLowerCase()}>`;
    }
}
/**
 * Take a selector and return its specificity according to the w3 specification.
 *
 * @see http://www.w3.org/TR/css3-selectors/#specificity
 * @param {string} selector
 * @returns number
 */
function _computeSpecificity(selector) {
    let a = 0;
    selector = selector.replace(/#[a-z0-9_-]+/gi, () => { a++; return ''; });
    let b = 0;
    selector = selector.replace(/(\.[a-z0-9_-]+)|(\[.*?\])/gi, () => { b++; return ''; });
    let c = 0;
    selector = selector.replace(/(^|\s+|:+)[a-z0-9_-]+/gi, a => { if (!a.includes(':not(')) c++; return ''; });
    return (a * 100) + (b * 10) + c;
}
/**
 * Take all the rules and modify them to contain information on their
 * specificity and to have normalized style.
 *
 * @see _computeSpecificity
 * @see _normalizeStyle
 * @param {Object} cssRules
 */
function _computeStyleAndSpecificityOnRules(cssRules) {
    for (const cssRule of cssRules) {
        if (!cssRule.style && cssRule.rawRule.style) {
            const style = _normalizeStyle(cssRule.rawRule.style);
            if (Object.keys(style).length) {
                Object.assign(cssRule,  { style, specificity: _computeSpecificity(cssRule.selector) });
            }
        }
    }
}
/**
 * Return an array of twelve table cells as JQuery elements.
 *
 * @returns {Element[]}
 */
function _createColumnGrid() {
    return new Array(12).fill().map(() => document.createElement('td'));
}
/**
 * Return a comment element with the given content, wrapped in an mso condition.
 *
 * @param {string} content
 * @returns {Comment}
 */
function _createMso(content='') {
    return document.createComment(`[if mso]>${content}<![endif]`)
}
/**
 * Return a table element, with its default styles and attributes, as well as
 * the applicable given attributes, if any.
 *
 * @see TABLE_ATTRIBUTES
 * @see TABLE_STYLES
 * @param {NamedNodeMap | Attr[]} [attributes] default: []
 * @returns {Element}
 */
function _createTable(attributes = []) {
    const table = document.createElement('table');
    Object.entries(TABLE_ATTRIBUTES).forEach(([att, value]) => table.setAttribute(att, value));
    for (const attr of attributes) {
        if (!(attr.name === 'width' && attr.value === '100%')) {
            table.setAttribute(attr.name, attr.value);
        }
    }
    table.style.setProperty('width', '100%', 'important');
    if (table.classList.contains('o_layout')) {
        // The top mailing element inherits the body's font size and line-height
        // and should keep them.
        const layoutStyles = {...TABLE_STYLES};
        delete layoutStyles['font-size'];
        delete layoutStyles['line-height'];
        Object.entries(layoutStyles).forEach(([att, value]) => table.style[att] = value)
    } else {
        for (const styleName in TABLE_STYLES) {
            if (!('style' in attributes && attributes.style.value.includes(styleName + ':'))) {
                table.style[styleName] = TABLE_STYLES[styleName];
            }
        }
    }
    return table;
}
/**
 * Take a Bootstrap grid column element and return its size, computed by using
 * its Bootstrap classes.
 *
 * @see RE_COL_MATCH
 * @param {Element} column
 * @returns {number}
 */
function _getColumnSize(column) {
    const colMatch = column.className.match(RE_COL_MATCH);
    const colOptions = colMatch[2] && colMatch[2].substr(1).split('-');
    const colSize = colOptions && (colOptions.length === 2 ? +colOptions[1] : +colOptions[0]) || 0;
    return colSize;
}
/**
 * Take a Bootstrap grid column element and return its offset size, computed by
 * using its Bootstrap classes.
 *
 * @see RE_OFFSET_MATCH
 * @param {Element} column
 * @returns {number}
 */
function _getColumnOffsetSize(column) {
    const offsetMatch = column.className.match(RE_OFFSET_MATCH);
    const offsetOptions = offsetMatch && offsetMatch[2] && offsetMatch[2].substr(1).split('-');
    const offsetSize = offsetOptions && (offsetOptions.length === 2 ? +offsetOptions[1] : +offsetOptions[0]) || 0;
    return offsetSize;
}
/**
 * Return the CSS rules which applies on an element, tweaked so that they are
 * browser/mail client ok.
 *
 * @param {Node} node
 * @param {Object[]} Array<{selector: string;
 *                          style: {[styleName]: string};
 *                          specificity: number;}>
 * @returns {Object} {[styleName]: string}
 */
function _getMatchedCSSRules(node, cssRules) {
    node.matches = node.matches || node.webkitMatchesSelector || node.mozMatchesSelector || node.msMatchesSelector || node.oMatchesSelector;
    const styles = cssRules.map((rule) => rule.style).filter(Boolean);

    // Add inline styles at the highest specificity.
    if (node.style.length) {
        const inlineStyles = {};
        for (const styleName of node.style) {
            inlineStyles[styleName] = node.style[styleName];
        }
        styles.push(inlineStyles);
    }

    const processedStyle = {};
    for (const style of styles) {
        for (const [key, value] of Object.entries(style)) {
            if (!processedStyle[key] || !processedStyle[key].includes('important') || value.includes('important')) {
                processedStyle[key] = value;
            }
        }
    }

    for (const [key, value] of Object.entries(processedStyle)) {
        if (value && value.endsWith('important')) {
            processedStyle[key] = value.replace(/\s*!important\s*$/, '');
        }
    };

    if (processedStyle.display === 'block' && !(node.classList && node.classList.contains('oe-nested'))) {
        delete processedStyle.display;
    }
    if (!processedStyle['box-sizing']) {
        processedStyle['box-sizing'] = 'border-box'; // This is by default with Bootstrap.
    }

    // The css generates all the attributes separately and not in simplified
    // form. In order to have a better compatibility (outlook for example) we
    // simplify the css tags. e.g. border-left-style: none; border-bottom-s ....
    // will be simplified in border-style = none
    for (const info of [
        {name: 'margin'},
        {name: 'padding'},
        {name: 'border', suffix: '-style', defaultValue: 'none'},
    ]) {
        const positions = ['top', 'right', 'bottom', 'left'];
        const positionalKeys = positions.map(position => `${info.name}-${position}${info.suffix || ''}`);
        const styles = positionalKeys.map(key => processedStyle[key]).filter(s => s);
        const hasVariableStyle = styles.some(style => style.includes('calc(') || style.includes('var('));
        const inherits = positionalKeys.some(key => ['inherit', 'initial'].includes((processedStyle[key] || '').trim()));
        if (styles.length && !hasVariableStyle && !inherits) {
            const propertyName = `${info.name}${info.suffix || ''}`;
            processedStyle[propertyName] = positionalKeys.every(key => processedStyle[positionalKeys[0]] === processedStyle[key])
                ? processedStyle[propertyName] = processedStyle[positionalKeys[0]] // top = right = bottom = left => property: [top];
                : positionalKeys.map(key => processedStyle[key] || (info.defaultValue || 0)).join(' '); // property: [top] [right] [bottom] [left];
            for (const prop of positionalKeys) {
                delete processedStyle[prop];
            }
        }
    };

    if (processedStyle['border-bottom-left-radius']) {
        processedStyle['border-radius'] = processedStyle['border-bottom-left-radius'];
        delete processedStyle['border-bottom-left-radius'];
        delete processedStyle['border-bottom-right-radius'];
        delete processedStyle['border-top-left-radius'];
        delete processedStyle['border-top-right-radius'];
    }

    // If the border styling is initial we remove it to simplify the css tags
    // for compatibility. Also, since we do not send a css style tag, the
    // initial value of the border is useless.
    for (const styleName in processedStyle) {
        if (styleName.includes('border') && processedStyle[styleName] === 'initial') {
            delete processedStyle[styleName];
        }
    };

    // text-decoration rule is decomposed in -line, -color and -style. This is
    // however not supported by many browser/mail clients and the editor does
    // not allow to change -color and -style rule anyway
    if (processedStyle['text-decoration-line']) {
        processedStyle['text-decoration'] = processedStyle['text-decoration-line'];
        delete processedStyle['text-decoration-line'];
        delete processedStyle['text-decoration-color'];
        delete processedStyle['text-decoration-style'];
        delete processedStyle['text-decoration-thickness'];
    }

    // flexboxes are not supported in Windows Outlook
    for (const styleName in processedStyle) {
        if (styleName.includes('flex') || `${processedStyle[styleName]}`.includes('flex')) {
            delete processedStyle[styleName];
        }
    }

    return processedStyle;
}
let lastComputedStyleElement;
let lastComputedStyle
/**
 * Return the value of the given style property on the given element. This
 * caches the last computed style so if it's called several times in a row for
 * the same element, we don't recompute it every time.
 *
 * @param {Element} element
 * @param {string} propertyName
 * @returns
 */
function _getStylePropertyValue(element, propertyName) {
    const computedStyle = lastComputedStyleElement === element ? lastComputedStyle : getComputedStyle(element)
    lastComputedStyleElement = element;
    lastComputedStyle = computedStyle;
    return computedStyle[propertyName] || element.style.getPropertyValue(propertyName);
}
/**
 * Equivalent to JQuery's `width` method. Returns the element's visible width.
 *
 * @param {Element} element
 * @returns {Number}
 */
function _getWidth(element) {
    return parseFloat(getComputedStyle(element).width.replace('px', '')) || 0;
}
/**
 * Equivalent to JQuery's `height` method. Returns the element's visible height.
 *
 * @param {Element} element
 * @returns {Number}
 */
function _getHeight(element) {
    return parseFloat(getComputedStyle(element).height.replace('px', '')) || 0;
}
/**
 * Hides the given node (or just its opening/closing tag) for Outlook with mso
 * conditional comments and, if needed, mso hide style.
 *
 * @param {Node} node
 * @param {false|'opening'|'closing'} [onlyHideTag=false]
 */
function _hideForOutlook(node, onlyHideTag = false) {
    if (!onlyHideTag) {
        node.setAttribute('style', `${node.getAttribute('style') || ''} mso-hide: all;`.trim());
    }
    node[onlyHideTag === 'closing' ? 'append' : 'before'](document.createComment('[if !mso]><!'));
    node[onlyHideTag === 'opening' ? 'prepend' : 'after'](document.createComment('<![endif]'));
}
/**
 * Return true if the given element is hidden.
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/offsetParent
 * @param {Element} element
 * @returns {boolean}
 */
function _isHidden(element) {
    return element.offsetParent === null;
}
/**
 * Take a css style declaration return a "normalized" version of it (as a
 * standard object) for the purposes of emails. This means removing its styles
 * that are invalid, describe animations or aren't standard css (webkit
 * extensions). It also involves adding the "!important" suffix to styles that
 * have that priority, so they can be handled without access to the full
 * declaration.
 *
 * @param {CSSStyleDeclaration} style
 * @returns {Object} {[styleName]: string}
 */
function _normalizeStyle(style) {
    const normalizedStyle = {};
    for (const styleName of style) {
        const value = style[styleName];
        if (value && !styleName.includes('animation') && !styleName.includes('-webkit') && _.isString(value)) {
            const normalizedStyleName = styleName.replace(/-(.)/g, (a, b) => b.toUpperCase());
            normalizedStyle[styleName] = style[normalizedStyleName];
            if (style.getPropertyPriority(styleName) === 'important') {
                normalizedStyle[styleName] += ' !important';
            }
        }
    }
    return normalizedStyle;
}
/**
 * Wrap a given element into a new parent, in place.
 *
 * @param {Element} element
 * @param {string} wrapperTag
 * @param {string} [wrapperClass] optional class to apply to the wrapper
 * @param {string} [wrapperStyle] optional style to apply to the wrapper
 * @returns {Element} the wrapper
 */
 function _wrap(element, wrapperTag, wrapperClass, wrapperStyle) {
    const wrapper = document.createElement(wrapperTag);
    if (wrapperClass) {
        wrapper.className = wrapperClass;
    }
    if (wrapperStyle) {
        wrapper.style.cssText = wrapperStyle;
    }
    element.parentElement.insertBefore(wrapper, element);
    wrapper.append(element);
    return wrapper;
}

export default {
    addTables: addTables,
    attachmentThumbnailToLinkImg: attachmentThumbnailToLinkImg,
    bootstrapToTable: bootstrapToTable,
    cardToTable: cardToTable,
    classToStyle: classToStyle,
    fontToImg: fontToImg,
    formatTables: formatTables,
    getCSSRules: getCSSRules,
    listGroupToTable: listGroupToTable,
    normalizeColors: normalizeColors,
    normalizeRem: normalizeRem,
    toInline: toInline,
};
