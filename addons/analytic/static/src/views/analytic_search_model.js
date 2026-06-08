import { SearchModel } from "@web/search/search_model";

const PLAN_REGEX = /^(?:x_)?(x_plan\d+_id|account_id)(_\d+)?$/;

export class AnalyticSearchModel extends SearchModel {
    getSearchItems(predicate) {
        let searchItems = super.getSearchItems(predicate);
        const mapped = Map.groupBy(
            searchItems.filter((f) => f.fieldName?.match(PLAN_REGEX)),
            (f) => f.fieldName.match(PLAN_REGEX)[1],
        );
        searchItems = searchItems.filter(
            (f) => !f.fieldName?.match(PLAN_REGEX) || mapped.has(f.fieldName)
        );
        searchItems.forEach((f) => {
            if (f.fieldName && mapped.has(f.fieldName) && mapped.get(f.fieldName).length > 1) {
                f.options = mapped.get(f.fieldName);
            }
        });
        return searchItems;
    }

    toggleDateGroupBy(searchItemId, intervalId) {
        if (typeof(intervalId) === "number") {
            this.toggleSearchItem(intervalId);
        } else {
            super.toggleDateGroupBy(searchItemId, intervalId);
        }
    }
}
