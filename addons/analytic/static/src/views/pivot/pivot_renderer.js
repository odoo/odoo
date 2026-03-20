import { PivotRenderer } from "@web/views/pivot/pivot_renderer";


export class AnalyticPivotRenderer extends PivotRenderer {

    /*
     * Override to avoid using incomplete groupByItems
     */
    onGroupBySelected({ itemId, optionId }) {
        if (typeof(optionId) === "number") {
            itemId = optionId;
        }
        let searchItems = this.env.searchModel.getSearchItems(
            (searchItem) =>
                ["groupBy", "dateGroupBy"].includes(searchItem.type) && !searchItem.custom
        )
        searchItems = [...searchItems, ...searchItems.flatMap((f) => f.options).filter((f) => typeof(f?.id) === "number")]
        const { fieldName } = searchItems.find(({ id }) => id === itemId);
        this.model.addGroupBy({ ...this.dropdown.cellInfo, fieldName, interval: optionId });
    }
}
