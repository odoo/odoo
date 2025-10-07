/** @odoo-module **/

import AdvancedFilterItem from "./advanced_filter_item.esm";
import {FilterMenu} from "@web/search/filter_menu/filter_menu";
import {patch} from "@web/core/utils/patch";
/**
 * Patches the FilterMenu for owl widgets.
 */
patch(FilterMenu, "web_advanced_search.FilterMenu", {
    components: {
        ...FilterMenu.components,
        AdvancedFilterItem,
    },
});

export default FilterMenu;
