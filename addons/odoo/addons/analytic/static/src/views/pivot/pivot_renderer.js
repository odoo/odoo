import { PivotRenderer } from "@web/views/pivot/pivot_renderer";


export class AnalyticPivotRenderer extends PivotRenderer {

    /*
     * Override to avoid using incomplete groupByItems
     */
    onGroupBySelected(type, payload) {
        if (typeof(payload.optionId) === "number") {
            let searchItems = this.env.searchModel.getSearchItems(
                (searchItem) =>
                    ["groupBy", "dateGroupBy"].includes(searchItem.type) && !searchItem.custom
            )
            searchItems = [...searchItems, ...searchItems.flatMap((f) => f.options).filter((f) => typeof(f?.id) === "number")]
            const { fieldName } = searchItems.find(({ id }) => id === payload.optionId);
            payload.fieldName = fieldName;
        }
        super.onGroupBySelected(type, payload);
    }
}
