odoo.define('web.KanbanTabsMobileMixin', function () {
"use strict";

const KanbanTabsMobileMixin = {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Update the tabs positions
     *
     * @param tabs - All existing tabs in the kanban
     * @param moveToIndex - The current Active tab in the index
     * @param $tabsContainer - the jquery container of the tabs
     * @private
     */
    _computeTabPosition(tabs, moveToIndex, $tabsContainer) {
        this._computeTabJustification(tabs, $tabsContainer);
        this._computeTabScrollPosition(tabs, moveToIndex, $tabsContainer);
    },
    /**
     * Update the tabs positions
     *
     * @param tabs - All existing tabs in the kanban
     * @param moveToIndex - The current Active tab in the index
     * @param $tabsContainer - the jquery container of the tabs
     * @private
     */
    _computeTabScrollPosition(tabs, moveToIndex, $tabsContainer) {
        if (tabs.length) {
            const lastItemIndex = tabs.length - 1;
            let scrollToLeft = 0;
            for (let i = 0; i < moveToIndex; i++) {
                const columnWidth = this._getTabWidth(tabs[i]);
                // apply
                if (moveToIndex !== lastItemIndex && i === moveToIndex - 1) {
                    const partialWidth = 0.75;
                    scrollToLeft += columnWidth * partialWidth;
                } else {
                    scrollToLeft += columnWidth;
                }
            }
            // Apply the scroll x on the tabs
            // XXX in case of RTL, should we use scrollRight?
            $tabsContainer.scrollLeft(scrollToLeft);
        }
    },

    /**
     * Compute the justify content of the kanban tab headers
     * @param tabs - All existing tabs in the kanban
     * @param $tabsContainer - the jquery container of the tabs
     * @private
     */
    _computeTabJustification(tabs, $tabsContainer) {
        if (tabs.length) {
            // Use to compute the sum of the width of all tab
            const widthChilds = tabs.reduce((total, column) => total + this._getTabWidth(column), 0);
            // Apply a space around between child if the parent length is higher then the sum of the child width
            $tabsContainer.toggleClass('justify-content-around', $tabsContainer.outerWidth() >= widthChilds);
        }
    },
    /**
     * Retrieve the outerWidth of a given tab
     *
     * @param tab
     * @returns {integer} outerWidth of the found column
     * @abstract
     */
    _getTabWidth(tab) {
    }
};
return KanbanTabsMobileMixin;
});
