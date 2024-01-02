/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import {descendants, preserveCursor} from "@web_editor/js/editor/odoo-editor/src/utils/utils";
const rowSize = 50; // 50px.
// Maximum number of rows that can be added when dragging a grid item.
export const additionalRowLimit = 10;

/**
 * Returns the grid properties: rowGap, rowSize, columnGap and columnSize.
 *
 * @private
 * @param {Element} rowEl the grid element
 * @returns {Object}
 */
export function _getGridProperties(rowEl) {
    const style = window.getComputedStyle(rowEl);
    const rowGap = parseFloat(style.rowGap);
    const columnGap = parseFloat(style.columnGap);
    const columnSize = (rowEl.clientWidth - 11 * columnGap) / 12;
    return {rowGap: rowGap, rowSize: rowSize, columnGap: columnGap, columnSize: columnSize};
}
/**
 * Sets the z-index property of the element to the maximum z-index present in
 * the grid increased by one (so it is in front of all the other elements).
 *
 * @private
 * @param {Element} element the element of which we want to set the z-index
 * @param {Element} rowEl the parent grid element of the element
 */
export function _setElementToMaxZindex(element, rowEl) {
    const childrenEls = [...rowEl.children].filter(el => el !== element
        && !el.classList.contains("o_we_grid_preview"));
    element.style.zIndex = Math.max(...childrenEls.map(el => el.style.zIndex)) + 1;
}
/**
 * Creates the background grid appearing everytime a change occurs in a grid.
 *
 * @private
 * @param {Element} rowEl
 * @param {Number} gridHeight
 */
export function _addBackgroundGrid(rowEl, gridHeight) {
    const gridProp = _getGridProperties(rowEl);
    const rowCount = Math.max(rowEl.dataset.rowCount, gridHeight);

    const backgroundGrid = renderToElement('web_editor.background_grid', {
        rowCount: rowCount + 1, rowGap: gridProp.rowGap, rowSize: gridProp.rowSize,
        columnGap: gridProp.columnGap, columnSize: gridProp.columnSize,
    });
    rowEl.prepend(backgroundGrid);
    return rowEl.firstElementChild;
}
/**
 * Updates the number of rows in the grid to the end of the lowest column
 * present in it.
 *
 * @private
 * @param {Element} rowEl
 */
export function _resizeGrid(rowEl) {
    const columnEls = [...rowEl.children].filter(c => c.classList.contains('o_grid_item'));
    rowEl.dataset.rowCount = Math.max(...columnEls.map(el => el.style.gridRowEnd)) - 1;
}
/**
 * Removes the properties and elements added to make the drag work.
 *
 * @private
 * @param {Element} rowEl
 * @param {Element} column
 */
export function _gridCleanUp(rowEl, columnEl) {
    columnEl.style.removeProperty('position');
    columnEl.style.removeProperty('top');
    columnEl.style.removeProperty('left');
    columnEl.style.removeProperty('height');
    columnEl.style.removeProperty('width');
    rowEl.style.removeProperty('position');
}
/**
 * Toggles the row (= child element of containerEl) in grid mode.
 *
 * @private
 * @param {Element} containerEl element with the class "container"
 */
export function _toggleGridMode(containerEl) {
    let rowEl = containerEl.querySelector(':scope > .row');
    const outOfRowEls = [...containerEl.children].filter(el => !el.classList.contains('row'));
    // Avoid an unwanted rollback that prevents from deleting the text.
    const avoidRollback = (el) => {
        for (const node of descendants(el)) {
            node.ouid = undefined;
        }
    };
    // Keep the text selection.
    const restoreCursor = !rowEl || outOfRowEls.length > 0 ?
        preserveCursor(containerEl.ownerDocument) : () => {};

    // For the snippets having elements outside of the row (and therefore not in
    // a column), create a column and put these elements in it so they can also
    // be placed in the grid.
    if (rowEl && outOfRowEls.length > 0) {
        const columnEl = document.createElement('div');
        columnEl.classList.add('col-lg-12');
        for (let i = outOfRowEls.length - 1; i >= 0; i--) {
            columnEl.prepend(outOfRowEls[i]);
        }
        avoidRollback(columnEl);
        rowEl.prepend(columnEl);
    }

    // If the number of columns is "None", create a column with the content.
    if (!rowEl) {
        rowEl = document.createElement('div');
        rowEl.classList.add('row');

        const columnEl = document.createElement('div');
        columnEl.classList.add('col-lg-12');

        const containerChildren = containerEl.children;
        // Looping backwards because elements are removed, so the indexes are
        // not lost.
        for (let i = containerChildren.length - 1; i >= 0; i--) {
            columnEl.prepend(containerChildren[i]);
        }
        avoidRollback(columnEl);
        rowEl.appendChild(columnEl);
        containerEl.appendChild(rowEl);
    }
    restoreCursor();

    // Converting the columns to grid and getting back the number of rows.
    const columnEls = rowEl.children;
    const columnSize = (rowEl.clientWidth) / 12;
    rowEl.style.position = 'relative';
    const rowCount = _placeColumns(columnEls, rowSize, 0, columnSize, 0) - 1;
    rowEl.style.removeProperty('position');
    rowEl.dataset.rowCount = rowCount;

    // Removing the classes that break the grid.
    const classesToRemove = [...rowEl.classList].filter(c => {
        return /^align-items/.test(c);
    });
    rowEl.classList.remove(...classesToRemove);

    rowEl.classList.add('o_grid_mode');
}
/**
 * Places each column in the grid based on their position and returns the
 * lowest row end.
 *
 * @private
 * @param {HTMLCollection} columnEls
 *      The children of the row element we are toggling in grid mode.
 * @param {Number} rowSize
 * @param {Number} rowGap
 * @param {Number} columnSize
 * @param {Number} columnGap
 * @returns {Number}
 */
function _placeColumns(columnEls, rowSize, rowGap, columnSize, columnGap) {
    let maxRowEnd = 0;
    const columnSpans = [];
    let zIndex = 1;
    const imageColumns = []; // array of boolean telling if it is a column with only an image.

    for (const columnEl of columnEls) {
        // Finding out if the images are alone in their column.
        let isImageColumn = _checkIfImageColumn(columnEl);
        const imageEl = columnEl.querySelector('img');
        // Checking if the column has a background color to take that into
        // account when computing its size and padding (to make it look good).
        const hasBackgroundColor = columnEl.classList.contains("o_cc");
        const isImageWithoutPadding = isImageColumn && !hasBackgroundColor;

        // Placing the column.
        const style = window.getComputedStyle(columnEl);
        // Horizontal placement.
        const columnLeft = isImageWithoutPadding ? imageEl.offsetLeft : columnEl.offsetLeft;
        // Getting the width of the column.
        const paddingLeft = parseFloat(style.paddingLeft);
        const width = isImageWithoutPadding ? parseFloat(imageEl.scrollWidth)
            : parseFloat(columnEl.scrollWidth) - (hasBackgroundColor ? 0 : 2 * paddingLeft);
        let columnSpan = Math.round((width + columnGap) / (columnSize + columnGap));
        if (columnSpan < 1) {
            columnSpan = 1;
        }
        const columnStart = Math.round(columnLeft / (columnSize + columnGap)) + 1;
        const columnEnd = columnStart + columnSpan;

        // Vertical placement.
        const columnTop = isImageWithoutPadding ? imageEl.offsetTop : columnEl.offsetTop;
        // Getting the top and bottom paddings and computing the row offset.
        const paddingTop = parseFloat(style.paddingTop);
        const paddingBottom = parseFloat(style.paddingBottom);
        const rowOffsetTop = Math.floor((paddingTop + rowGap) / (rowSize + rowGap));
        // Getting the height of the column.
        const height = isImageWithoutPadding ? parseFloat(imageEl.scrollHeight)
            : parseFloat(columnEl.scrollHeight) - (hasBackgroundColor ? 0 : paddingTop + paddingBottom);
        const rowSpan = Math.ceil((height + rowGap) / (rowSize + rowGap));
        const rowStart = Math.round(columnTop / (rowSize + rowGap)) + 1 + (hasBackgroundColor || isImageWithoutPadding ? 0 : rowOffsetTop);
        const rowEnd = rowStart + rowSpan;

        columnEl.style.gridArea = `${rowStart} / ${columnStart} / ${rowEnd} / ${columnEnd}`;
        columnEl.classList.add('o_grid_item');

        // Adding the grid classes.
        columnEl.classList.add('g-col-lg-' + columnSpan, 'g-height-' + rowSpan);
        // Setting the initial z-index.
        columnEl.style.zIndex = zIndex++;
        // Setting the paddings.
        if (hasBackgroundColor) {
            columnEl.style.setProperty("--grid-item-padding-y", `${paddingTop}px`);
            columnEl.style.setProperty("--grid-item-padding-x", `${paddingLeft}px`);
        }
        // Reload the images.
        _reloadLazyImages(columnEl);

        maxRowEnd = Math.max(rowEnd, maxRowEnd);
        columnSpans.push(columnSpan);
        imageColumns.push(isImageColumn);
    }

    for (const [i, columnEl] of [...columnEls].entries()) {
        // Removing padding and offset classes.
        const regex = /^(((pt|pb)\d{1,3}$)|col-lg-|offset-lg-)/;
        const toRemove = [...columnEl.classList].filter(c => {
            return regex.test(c);
        });
        columnEl.classList.remove(...toRemove);
        columnEl.classList.add('col-lg-' + columnSpans[i]);

        // If the column only has an image, convert it.
        if (imageColumns[i]) {
            _convertImageColumn(columnEl);
        }
    }

    return maxRowEnd;
}
/**
 * Removes and sets back the 'src' attribute of the images inside a column.
 * (To avoid the disappearing image problem in Chrome).
 *
 * @private
 * @param {Element} columnEl
 */
export function _reloadLazyImages(columnEl) {
    const imageEls = columnEl.querySelectorAll('img');
    for (const imageEl of imageEls) {
        const src = imageEl.getAttribute("src");
        imageEl.src = '';
        imageEl.src = src;
    }
}
/**
 * Computes the column and row spans of the column thanks to its width and
 * height and returns them. Also adds the grid classes to the column.
 *
 * @private
 * @param {Element} rowEl
 * @param {Element} columnEl
 * @param {Number} columnWidth the width in pixels of the column.
 * @param {Number} columnHeight the height in pixels of the column.
 * @returns {Object}
 */
export function _convertColumnToGrid(rowEl, columnEl, columnWidth, columnHeight) {
    // First, checking if the column only contains an image and if it is the
    // case, converting it.
    if (_checkIfImageColumn(columnEl)) {
        _convertImageColumn(columnEl);
    }

    // Computing the column and row spans.
    const gridProp = _getGridProperties(rowEl);
    const columnColCount = Math.round((columnWidth + gridProp.columnGap) / (gridProp.columnSize + gridProp.columnGap));
    const columnRowCount = Math.ceil((columnHeight + gridProp.rowGap) / (gridProp.rowSize + gridProp.rowGap));

    // Removing the padding and offset classes.
    const regex = /^(pt|pb|col-|offset-)/;
    const toRemove = [...columnEl.classList].filter(c => regex.test(c));
    columnEl.classList.remove(...toRemove);

    // Adding the grid classes.
    columnEl.classList.add('g-col-lg-' + columnColCount, 'g-height-' + columnRowCount, 'col-lg-' + columnColCount);
    columnEl.classList.add('o_grid_item');

    return {columnColCount: columnColCount, columnRowCount: columnRowCount};
}
/**
 * Removes the grid properties from the grid column when it becomes a normal
 * column.
 *
 * @param {Element} columnEl
 */
export function _convertToNormalColumn(columnEl) {
    const gridSizeClasses = columnEl.className.match(/(g-col-lg|g-height)-[0-9]+/g);
    columnEl.classList.remove("o_grid_item", "o_grid_item_image", "o_grid_item_image_contain", ...gridSizeClasses);
    columnEl.style.removeProperty("z-index");
    columnEl.style.removeProperty("--grid-item-padding-x");
    columnEl.style.removeProperty("--grid-item-padding-y");
    columnEl.style.removeProperty("grid-area");
}
/**
 * Checks whether the column only contains an image or not. An image is
 * considered alone if the column only contains empty textnodes and line breaks
 * in addition to the image. Note that "image" also refers to an image link
 * (i.e. `a > img`).
 *
 * @private
 * @param {Element} columnEl
 * @returns {Boolean}
 */
export function _checkIfImageColumn(columnEl) {
    let isImageColumn = false;
    const imageEls = columnEl.querySelectorAll(":scope > img, :scope > a > img");
    const columnChildrenEls = [...columnEl.children].filter(el => el.nodeName !== 'BR');
    if (imageEls.length === 1 && columnChildrenEls.length === 1) {
        // If there is only one image and if this image is the only "real"
        // child of the column, we need to check if there is text in it.
        const textNodeEls = [...columnEl.childNodes].filter(el => el.nodeType === Node.TEXT_NODE);
        const areTextNodesEmpty = [...textNodeEls].every(textNodeEl => textNodeEl.nodeValue.trim() === '');
        isImageColumn = areTextNodesEmpty;
    }
    return isImageColumn;
}
/**
 * Removes the line breaks and textnodes of the column, adds the grid class and
 * sets the image width to default so it can be displayed as expected. Also
 * blocks the edition of the column.
 *
 * @private
 * @param {Element} columnEl a column containing only an image.
 */
function _convertImageColumn(columnEl) {
    columnEl.querySelectorAll('br').forEach(el => el.remove());
    const textNodeEls = [...columnEl.childNodes].filter(el => el.nodeType === Node.TEXT_NODE);
    textNodeEls.forEach(el => el.remove());
    const imageEl = columnEl.querySelector('img');
    columnEl.classList.add('o_grid_item_image');
    imageEl.style.removeProperty('width');
}
