/** @odoo-module **/

import { GraphModel } from "@web/views/graph/graph_model";

export class ProjectTaskGraphModel extends GraphModel {
    _getDefaultFilterLabel(fieldName) {
        if (fieldName === "project_id") {
            return this.env._t("🔒 Private");
        }
        return super._getDefaultFilterLabel(fieldName);
    }
}
