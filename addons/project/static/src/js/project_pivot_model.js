/** @odoo-module **/

import { PivotModel } from "@web/views/pivot/pivot_model";

export class ProjectTaskPivotModel extends PivotModel {
    /**
     * @override
     */
    _getEmptyGroupLabel(fieldName) {
        if (fieldName === "project_id") {
            return this.env._t("Private");
        } else if (fieldName === "user_ids") {
            return this.env._t("Unassigned");
        } else {
            return super._getEmptyGroupLabel(fieldName);
        }
    }
}
