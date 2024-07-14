/** @odoo-module **/

import { SearchBar } from "@web/search/search_bar/search_bar";

export class MrpDisplaySearchBar extends SearchBar {
    removeFacet(facet) {
        if (facet.color === "info") {
            this.env.searchModel.state.workorderFilters.forEach((f) => {
                f.isActive = false;
            });
            return;
        } else if (facet.type === "favorite" && this.env.searchModel.workorders) {
            for (const filter of this.env.searchModel.state.workorderFilters) {
                filter.isActive = false;
            }
        }
        return super.removeFacet(facet);
    }
}
MrpDisplaySearchBar.template = "mrp_workorder.MrpDisplaySearchBar";
