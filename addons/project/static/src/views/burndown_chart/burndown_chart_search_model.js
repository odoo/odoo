/** @odoo-module */

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
                if (this.stageIdSearchItemId && this.dateSearchItemId) {
                    return;
                }
                switch (searchItem.fieldName) {
                    case 'date':
                        this.dateSearchItemId = searchItem.id;
                        break;
                    case 'stage_id':
                        this.stageIdSearchItemId = searchItem.id;
                        break;
                }
            }
        }
    }

    /**
     * @override
     */
    deactivateGroup(groupId) {
        // Prevent removing Date & Stage group by from the search
        if (this.searchItems[this.stageIdSearchItemId].groupId == groupId && this.searchItems[this.dateSearchItemId].groupId) {
            this._addGroupByNotification(this.env._t("Date and Stage"));
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
                    this._addGroupByNotification(this.env._t("Date"));
                }
            }
        }
        super.toggleDateGroupBy(...arguments);
    }

    /**
     * @override
     */
    toggleSearchItem(searchItemId) {
        // Ensure that stage_id is always selected.
        if (searchItemId === this.stageIdSearchItemId
            && this.query.some(queryElem => queryElem.searchItemId === searchItemId)) {
            this._addGroupByNotification(this.env._t("Stage"));
            return;
        }
        super.toggleSearchItem(...arguments);
    }

    /**
     * Adds a notification relative to the group by constraint of the Burndown Chart.
     * @param fieldName The field name(s) the notification has to be related to.
     * @private
     */
    _addGroupByNotification(fieldName) {
        const notif = this.env._t("The Burndown Chart must be grouped by");
        this.notificationService.add(
            `${notif} ${fieldName}`,
            { type: "danger" }
        );
    }

    /**
     * @override
     */
    async _notify() {
        // Ensure that we always group by date firstly and by stage_id secondly
        let stageIdIndex = -1;
        let dateIndex = -1;
        for (const [index, queryElem] of this.query.entries()) {
            if (stageIdIndex !== -1 && dateIndex !== -1) {
                break;
            }
            switch (queryElem.searchItemId) {
                case this.dateSearchItemId:
                    dateIndex = index;
                    break;
                case this.stageIdSearchItemId:
                    stageIdIndex = index;
                    break;
            }
        }
        if (stageIdIndex > 0) {
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
