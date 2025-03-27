/** @odoo-module **/

import AdvancedFilterItem from "./advanced_filter_item.esm";
import FilterMenu from "web.FilterMenu";
import {patch} from "@web/core/utils/patch";

/**
 * Patches the FilterMenu for legacy widgets.
 *
 * Tree views still use this old legacy widget, so we need to patch it.
 * This is likely to disappear in 17.0
 */
patch(FilterMenu, "web_advanced_search.legacy.FilterMenu", {
    components: {
        ...FilterMenu.components,
        AdvancedFilterItem,
    },
});

export default FilterMenu;
