// @ts-check

/** @module @web/views/pivot/pivot_search_model - SearchModel extension restoring pivot_row_groupby from saved favorites */

/** @type {any} */

import { SearchModel } from "@web/search/search_model";

const Base = SearchModel;

/**
 * Search model extension for the pivot view.
 *
 * Overrides group-by resolution so that favorites saved with
 * `pivot_row_groupby` in their context restore the correct row
 * grouping instead of using the default search-item group-bys.
 */
export class PivotSearchModel extends Base {
    /**
     * Build the ir.filter description, flagging that we are serializing
     * so `_getSearchItemGroupBys` falls back to the default behavior.
     *
     * @returns {Object}
     */
    _getIrFilterDescription() {
        this.preparingIrFilterDescription = true;
        const result = super._getIrFilterDescription(...arguments);
        this.preparingIrFilterDescription = false;
        return result;
    }

    /**
     * Return group-by specs for the given active search item. When a
     * favorite carries `pivot_row_groupby` in its context, those are
     * used directly (unless we are currently building an ir.filter
     * description).
     *
     * @param {Object} activeItem - the currently active search item
     * @returns {string[]}
     */
    _getSearchItemGroupBys(activeItem) {
        const { searchItemId } = activeItem;
        const { context, type } = this.searchItems[searchItemId];
        if (
            !this.preparingIrFilterDescription &&
            type === "favorite" &&
            context.pivot_row_groupby
        ) {
            return context.pivot_row_groupby;
        }
        return super._getSearchItemGroupBys(...arguments);
    }
}
