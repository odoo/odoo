/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";

export class TimesheetGridSearchModel extends SearchModel {
    /**
     * @override
     */
    setup(services) {
        super.setup(services);
        this.notificationService = useService("notification");
    }

    toggleDateGroupBy(searchItemId, intervalId) {
        const searchItem = this.searchItems[searchItemId];
        if (searchItem.type !== "dateGroupBy") {
            return;
        }
        intervalId = intervalId || searchItem.defaultIntervalId;
        const index = this.query.findIndex(
            (queryElem) =>
                queryElem.searchItemId === searchItemId &&
                "intervalId" in queryElem &&
                queryElem.intervalId === intervalId
        );
        if (index === -1) {
            this.notificationService.add(_t("Grouping by date is not supported"), {
                type: "danger",
            });
        } else {
            super.toggleDateGroupBy();
        }
    }
}
