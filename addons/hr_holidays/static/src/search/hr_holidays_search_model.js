import { SearchModel } from "@web/search/search_model";


export class HrHolidaysSearchModel extends SearchModel {
    _getIntervalOptions(searchItem) {
        const intervalOptions = super._getIntervalOptions(searchItem);
        if (searchItem.type !== "dateGroupBy") {
            return intervalOptions;
        }
        // filters out the "group by" intervals that are too precise (weeks/days/etc.)
        const allowedIntervals = ["month", "quarter", "year"];
        return intervalOptions.filter((option) => allowedIntervals.includes(option.id));
    }
}
