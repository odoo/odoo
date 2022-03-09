/** @odoo-module **/

import { PivotModel } from "@web/views/pivot/pivot_model";

export class BurndownChartPivotModel extends PivotModel {
    /**
     * @protected
     * @override
     */
    async _loadData(config, prune = true) {
        config.metaData.measures.__count.string = '# of Tasks';
        await super._loadData(config, prune);
    }
}
