import { SearchModel } from "@web/search/search_model";

export class GraphSearchModel extends SearchModel {
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
