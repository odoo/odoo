import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class OfflineActionHelper extends Component {
    static template = "web.OfflineActionHelper";
    static props = [];

    setup() {
        const offlineService = useService("offline");

        this.searches = null;
        onWillStart(async () => {
            const { actionId, viewType } = this.env.config;
            this.searches = await offlineService.getAvailableSearches(actionId, viewType);
        });
    }

    onResetFilters() {
        this.env.searchModel.applySearch(this.searches[0]);
    }
}
