/** @odoo-module **/

export const ColumnLayoutMixin = {
    /**
     * Calculates the number of columns for the mobile or desktop version.
     * If all elements don't have the same size, returns "custom".
     *
     * @private
     * @param {HTMLCollection} columnEls - elements in the .row container
     * @param {boolean} isMobile
     * @returns {integer|string} number of columns or "custom"
     */
    _getNbColumns(columnEls, isMobile) {
        if (!columnEls || !columnEls[0]) {
            return 0;
        }
        if (this._areColsCustomized(columnEls, isMobile)) {
            return "custom";
        }

        const resolutionModifier = isMobile ? "" : "lg-";
        const colRegex = new RegExp(`(?:^|\\s+)col-${resolutionModifier}(\\d{1,2})(?!\\S)`);
        const colSize = parseInt(columnEls[0].className.match(colRegex)?.[1] || 12);
        const offsetSize = this._getFirstItem(columnEls, isMobile).classList
            .contains(`offset-${resolutionModifier}1`) ? 1 : 0;

        return Math.floor((12 - offsetSize) / colSize);
    },
    /**
     * Gets the first item, whether it has a mobile order or not.
     *
     * @private
     * @param {HTMLCollection} columnEls - elements in the .row container
     * @param {boolean} isMobile
     * @returns {HTMLElement} first HTMLElement in order
     */
    _getFirstItem(columnEls, isMobile) {
        return isMobile && [...columnEls].find(el => el.style.order === "0") || columnEls[0];
    },
    /**
     * Adds mobile order and the reset class for large screens.
     *
     * @private
     * @param {HTMLCollection} columnEls - elements in the .row container
     */
    _addMobileOrders(columnEls) {
        for (let i = 0; i < columnEls.length; i++) {
            columnEls[i].style.order = i;
            columnEls[i].classList.add("order-lg-0");
        }
    },
    /**
     * Removes mobile orders and the reset class for large screens.
     *
     * @private
     * @param {HTMLCollection} columnEls - elements in the .row container
     */
    _removeMobileOrders(columnEls) {
        for (const el of columnEls) {
            el.style.order = "";
            el.classList.remove("order-lg-0");
        }
    },
    /**
     * Checks whether some columns were resized or were added offsets manually.
     *
     * @private
     * @param {HTMLElement} columnEls
     * @param {boolean} isMobile
     * @returns {boolean}
     */
    _areColsCustomized(columnEls, isMobile) {
        if (!columnEls || !columnEls[0]) {
            return false;
        }
        const resolutionModifier = isMobile ? "" : "lg-";
        const colRegex = new RegExp(`(?:^|\\s+)col-${resolutionModifier}(\\d{1,2})(?!\\S)`);
        const colSize = parseInt(columnEls[0].className.match(colRegex)?.[1] || 12);

        // Cases where we know the columns sizes and/or offsets are NOT custom:
        // - if all columns have an equal size AND
        //     - if there are no offsets OR
        //     - if, with 5 columns, there is exactly one offset-1 and it's on
        //       the 1st item
        // Any other case is custom.
        const allColsSizesEqual = [...columnEls].every((columnEl) =>
            parseInt(columnEl.className.match(colRegex)?.[1] || 12) === colSize);
        if (!allColsSizesEqual) {
            return true;
        }
        const offsetRegex = new RegExp(`(?:^|\\s+)offset-${resolutionModifier}[1-9][0-1]?(?!\\S)`);
        const nbOffsets = [...columnEls]
            .filter((columnEl) => columnEl.className.match(offsetRegex)).length;
        if (nbOffsets === 0) {
            return false;
        }
        if (nbOffsets === 1 && colSize === 2 && this._getFirstItem(columnEls, isMobile).className
                .match(`offset-${resolutionModifier}1`)) {
            return false;
        }
        return true;
    },
    /**
     * Fill in the gap left by a removed item having a mobile order class.
     *
     * @param {HTMLElement} parentEl the removed item parent
     * @param {Number} itemOrder the removed item mobile order
     */
    _fillRemovedItemGap(parentEl, itemOrder) {
        [...parentEl.children].forEach(el => {
            const elOrder = parseInt(el.style.order);
            if (elOrder > itemOrder) {
                el.style.order = elOrder - 1;
            }
        });
    },
};
