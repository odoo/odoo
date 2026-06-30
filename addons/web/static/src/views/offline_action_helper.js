import { Component, onWillStart, plugin } from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";

export class OfflineActionHelper extends Component {
    static template = "web.OfflineActionHelper";
    static props = [];

    setup() {
        const offlinePlugin = plugin(OfflinePlugin);

        this.searches = null;
        onWillStart(async () => {
            const { actionId, viewType } = this.env.config;
            this.searches = await offlinePlugin.getAvailableSearches(actionId, viewType);
        });
    }

    onResetFilters() {
        this.env.searchModel.applySearch(this.searches[0]);
    }
}
