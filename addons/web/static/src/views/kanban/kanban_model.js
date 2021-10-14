/** @odoo-module **/

import { RelationalModel } from "@web/views/relational_model";

export class KanbanModel extends RelationalModel {
    setup(params = {}) {
        super.setup(...arguments);

        this.defaultGroupBy = params.defaultGroupBy || false;
    }

    /**
     * Applies the default groupBy defined on the arch when not in a dialog.
     * @override
     */
    async load(params = {}) {
        const groupBy = params.groupBy.slice();
        if (this.defaultGroupBy && !this.env.inDialog) {
            groupBy.push(this.defaultGroupBy);
        }
        return super.load({ ...params, groupBy: groupBy.slice(0, 1) });
    }
}
