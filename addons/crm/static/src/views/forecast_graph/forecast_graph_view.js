/** @odoo-module **/

import { registry } from "@web/core/registry";
import { GraphViewDescription } from "@web/views/graph/graph_view";
import { ForecastSearchModel } from "@crm/views/forecast_search_model";

class ForecastGraphSearchModel extends ForecastSearchModel {
    /**
     * @override
     * @private
     */
    _getIrFilterDescription() {
        this.preparingIrFilterDescription = true;
        const result = super._getIrFilterDescription(...arguments);
        this.preparingIrFilterDescription = false;
        return result;
    }

    _getSearchItemGroupBys(activeItem) {
        const { searchItemId } = activeItem;
        const { context, type } = this.searchItems[searchItemId];
        if (!this.preparingIrFilterDescription && type === "favorite" && context.graph_groupbys) {
            return context.graph_groupbys;
        }
        return super._getSearchItemGroupBys(...arguments);
    }
}

export class ForecastGraphViewDescription extends GraphViewDescription {
    static SearchModel = ForecastGraphSearchModel;

    onSearchFilter() {

    }
};

registry.category("views_new").add("forecast_graph", ForecastGraphViewDescription);
