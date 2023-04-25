/** @odoo-module **/

import { GraphModel } from "@web/views/graph/graph_model";

export class ProjectTaskGraphModel extends GraphModel {
    _getDefaultFilterLabel(field) {
        if (field.fieldName === "project_id") {
            return this.env._t("🔒 Private");
        }
        return super._getDefaultFilterLabel(field);
    }
}
