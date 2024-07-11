/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PivotModel } from "@web/views/pivot/pivot_model";

export class ProjectTaskPivotModel extends PivotModel {
    /**
     * @override
     */
    _getEmptyGroupLabel(fieldName) {
        if (fieldName === "project_id") {
            return _t("Private");
        } else if (fieldName === "user_ids") {
            return _t("Unassigned");
        } else {
            return super._getEmptyGroupLabel(fieldName);
        }
    }
}
