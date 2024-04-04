/** @odoo-module **/

import { CrmKanbanModel } from "@crm/views/crm_kanban/crm_kanban_model";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class ForecastKanbanModel extends CrmKanbanModel {
    /**
     * Set end of temporal period in search model.
     * This allows kanban to load new months one at a time.
     * @override
     */
    async _loadGroupedList() {
        const res = await super._loadGroupedList(...arguments);
        const searchModel = this.env.searchModel;
        if (searchModel.isTemporalFilterEnabled()) {
            const lastGroup = res.groups.filter((grp) => grp.value).slice(-1)[0];
            searchModel.setTemporalEnd(deserializeDateTime(lastGroup.range.to));
        }
        return res;
    }
}
