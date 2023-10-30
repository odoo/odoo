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
        if (!columnEls) {
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
     * Retrieves the mobile order class as a match array if there is one.
     *
     * @private
     * @param {HTMLElement} el
     * @returns {Array|null} class match ["order-XX", "XX"]
     */
    _getItemMobileOrder(el) {
        return el.className.match(/\border-([0-9]+)\b/);
    },
    /**
     * Gets the first item, whether it has a mobile order class or not.
     *
     * @private
     * @param {HTMLCollection} columnEls - elements in the .row container
     * @param {boolean} isMobile
     * @returns {HTMLElement} first HTMLElement in order
     */
    _getFirstItem(columnEls, isMobile) {
        return isMobile && [...columnEls].find(el => el.classList.contains("order-0"))
            || columnEls[0];
    },
    /**
     * Adds the classes for mobile order.
     *
     * @private
     * @param {HTMLCollection} columnEls - elements in the .row container
     */
    _addMobileOrders(columnEls) {
        for (let i = 0; i < columnEls.length; i++) {
            const mobileOrderClass = `order-${i}`;
            columnEls[i].classList.add(mobileOrderClass, "order-lg-0");
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
};
