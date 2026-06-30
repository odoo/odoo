import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";


export class BurndownChartSearchModel extends SearchModel {

    /**
     * @override
     */
    setup(services) {
        this.notificationService = useService("notification");
        super.setup(...arguments);
    }

    /**
     * @override
     */
    async load(config) {
        await super.load(...arguments);
        // Store date and stage_id searchItemId in the SearchModel for reuse in other functions.
        for (const searchItem of Object.values(this.searchItems)) {
            if (['dateGroupBy', 'groupBy'].includes(searchItem.type)) {
                if (this.stageIdSearchItemId && this.dateSearchItemId && this.isClosedSearchItemId) {
                    return;
                }
                switch (searchItem.fieldName) {
                    case 'date':
                        this.dateSearchItemId = searchItem.id;
                        break;
                    case 'stage_id':
                        this.stageIdSearchItemId = searchItem.id;
                        break;
                    case 'is_closed':
                        this.isClosedSearchItemId = searchItem.id;
                        break;
                }
            }
        }
    }

    /**
     * @override
     */
    deactivateGroup(groupId) {
        // Prevent removing 'Date & Stage' and 'Date & is closed' group by from the search
        if (this.searchItems[this.dateSearchItemId].groupId == groupId) {
            if (this.query.some(queryElem => [this.stageIdSearchItemId, this.isClosedSearchItemId].includes(queryElem.searchItemId))){
                this._addGroupByNotification(_t("The report should be grouped either by \"Stage\" to represent a Burndown Chart or by \"Is Closed\" to represent a Burn-up chart. Without one of these groupings applied, the report will not provide relevant information."));
            }
            return;
        }
        super.deactivateGroup(groupId);
    }

    /**
     * @override
     */
    toggleDateGroupBy(searchItemId, intervalId) {
        // Ensure that there is always one and only one date group by selected.
        if (searchItemId === this.dateSearchItemId) {
            let filtered_query = [];
            let triggerNotification = false;
            for (const queryElem of this.query) {
                if (queryElem.searchItemId !== searchItemId) {
                    filtered_query.push(queryElem);
                } else if (queryElem.intervalId === intervalId) {
                    triggerNotification = true;
                }
            }
            if (filtered_query.length !== this.query.length) {
                this.query = filtered_query;
                if (triggerNotification) {
                    this._addGroupByNotification(_t("The Burndown Chart must be grouped by Date"));
                }
            }
        }
        super.toggleDateGroupBy(...arguments);
    }

    /**
     * @override
     * Ensure here that there is always either the 'stage' or the 'is_closed' searchItemId inside the query.
     */
    toggleSearchItem(searchItemId) {
        // if the current searchItem stage/is_closed, the counterpart is added before removing the current searchItem
        if (searchItemId === this.isClosedSearchItemId){
            super.toggleSearchItem(this.stageIdSearchItemId);
        } else if (searchItemId === this.stageIdSearchItemId){
            super.toggleSearchItem(this.isClosedSearchItemId);
        }
        super.toggleSearchItem(...arguments);
    }

    /**
     * Adds a notification related to the group by constraint of the Burndown Chart.
     * @param body The message to display in the notification.
     * @private
     */
    _addGroupByNotification(body) {
        this.notificationService.add(
            body,
            { type: "danger" }
        );
    }

    /**
     * @override
     */
    async _notify() {
        // Ensure that we always group by date first and by stage_id/is_closed second
        let stageIdIndex = -1;
        let dateIndex = -1;
        let isClosedIndex = -1;
        for (const [index, queryElem] of this.query.entries()) {
            if (dateIndex !== -1 && (stageIdIndex !== -1 || isClosedIndex !== -1)) {
                break;
            }
            switch (queryElem.searchItemId) {
                case this.dateSearchItemId:
                    dateIndex = index;
                    break;
                case this.stageIdSearchItemId:
                    stageIdIndex = index;
                    break;
                case this.isClosedSearchItemId:
                    isClosedIndex = index;
                    break;
            }
        }
        if (isClosedIndex > 0) {
            if (isClosedIndex > dateIndex) {
                dateIndex += 1;
            }
            this.query.splice(0, 0, this.query.splice(stageIdIndex, 1)[0]);
        } else if (stageIdIndex > 0) {
            if (stageIdIndex > dateIndex) {
                dateIndex += 1;
            }
            this.query.splice(0, 0, this.query.splice(stageIdIndex, 1)[0]);
        }
        if (dateIndex > 0) {
            this.query.splice(0, 0, this.query.splice(dateIndex, 1)[0]);
        }
        await super._notify(...arguments);
    }

}
