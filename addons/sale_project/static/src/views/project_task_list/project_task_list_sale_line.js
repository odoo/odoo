/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProjectTaskListRenderer } from "@project/views/project_task_list/project_task_list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";

patch(ProjectTaskListRenderer.prototype, {
    /**
     * This method prevents from computing the selection once for each cell when
     * rendering the list. Indeed, `selection` is a getter which browses all
     * records, so computing it for each cell slows down the rendering a lot on
     * large tables. Moreover, it also prevents from iterating over the selection
     * to compare tasks' partners.
     *
     * It returns true iff the selected tasks all have the same partner.
     */
    haveSelectedTasksSamePartner() {
        if (this._haveSelectedTasksSamePartner === undefined) {
            const selection = this.props.list.selection;
            const partnerId = selection.length && getRawValue(selection[0], "partner_id");
            this._haveSelectedTasksSamePartner = selection.every(
                (task) => getRawValue(task, "partner_id") === partnerId
            );
            Promise.resolve().then(() => {
                delete this._haveSelectedTasksSamePartner;
            });
        }
        return this._haveSelectedTasksSamePartner;
    },

    isCellReadonly(column, record) {
        let readonly = false;
        if (column.name === "sale_line_id") {
            readonly = !this.haveSelectedTasksSamePartner();
        }
        return readonly || super.isCellReadonly(column, record);
    }
});
