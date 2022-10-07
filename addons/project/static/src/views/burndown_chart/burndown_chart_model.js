/** @odoo-module **/

import { GraphModel } from "@web/views/graph/graph_model";

export class BurndownChartModel extends GraphModel {
    /**
     * @protected
     * @override
     */
    async _loadDataPoints(metaData) {
        metaData.measures.__count.string = this.env._t('# of Tasks');
        return super._loadDataPoints(metaData);
    }
}
