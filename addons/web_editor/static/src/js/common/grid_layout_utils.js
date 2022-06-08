/** @odoo-module **/
'use strict';

import {qweb} from 'web.core';
const rowSize = 50; // 50px.

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
    const childrenEls = [...rowEl.children].filter(el => el !== element);
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

    const backgroundGrid = qweb.render('web_editor.background_grid', {
        rowCount: rowCount + 1, rowGap: gridProp.rowGap, rowSize: gridProp.rowSize,
        columnGap: gridProp.columnGap, columnSize: gridProp.columnSize,
    });
    rowEl.insertAdjacentHTML("afterbegin", backgroundGrid);
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
    let rowEl = containerEl.querySelector('.row');

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
        rowEl.appendChild(columnEl);
        containerEl.appendChild(rowEl);
    }

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
    const columnCount = columnEls.length; // number of column in the grid.
    for (const columnEl of columnEls) {
        const style = window.getComputedStyle(columnEl);
        // Horizontal placement.
        const columnLeft = columnEl.offsetLeft;
        // Getting the width of the column.
        const paddingLeft = parseFloat(style.paddingLeft);
        const width = parseFloat(columnEl.scrollWidth) - 2 * paddingLeft;
        const columnSpan = Math.ceil((width + columnGap) / (columnSize + columnGap));
        const columnStart = Math.round(columnLeft / (columnSize + columnGap)) + 1;
        const columnEnd = columnStart + columnSpan;

        // Vertical placement.
        const columnTop = columnEl.offsetTop;
        // Getting the top and bottom paddings and computing the row offset.
        const paddingTop = parseFloat(style.paddingTop);
        const paddingBottom = parseFloat(style.paddingBottom);
        const rowOffsetTop = Math.floor((paddingTop + rowGap) / (rowSize + rowGap));
        // Getting the height of the column.
        const height = parseFloat(columnEl.scrollHeight) - paddingTop - paddingBottom;
        const rowSpan = Math.ceil((height + rowGap) / (rowSize + rowGap));
        const rowStart = Math.round(columnTop / (rowSize + rowGap)) + 1 + rowOffsetTop;
        const rowEnd = rowStart + rowSpan;

        columnEl.style.gridArea = `${rowStart} / ${columnStart} / ${rowEnd} / ${columnEnd}`;
        columnEl.classList.add('o_grid_item');

        // Removing the grid classes (since they end with 0) and adding the
        // correct ones.
        const regex = /^(g-)/;
        const toRemove = [...columnEl.classList].filter(c => {
            return regex.test(c);
        });
        columnEl.classList.remove(...toRemove);
        columnEl.classList.add('g-col-lg-' + columnSpan, 'g-height-' + rowSpan);

        // Setting the initial z-index to the number of columns.
        columnEl.style.zIndex = columnCount;

        // Reload the images.
        _reloadLazyImages(columnEl);

        maxRowEnd = Math.max(rowEnd, maxRowEnd);
        columnSpans.push(columnSpan);
    }

    // Removing padding and offset classes.
    for (const [i, columnEl] of [...columnEls].entries()) {
        const regex = /^(pt|pb|col-|offset-)/;
        const toRemove = [...columnEl.classList].filter(c => {
            return regex.test(c);
        });
        columnEl.classList.remove(...toRemove);
        columnEl.classList.add('col-lg-' + columnSpans[i]);
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
        const src = imageEl.src;
        imageEl.src = '';
        imageEl.src = src;
    }
}
