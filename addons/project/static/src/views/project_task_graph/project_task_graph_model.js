/** @odoo-module **/

import { GraphModel } from "@web/views/graph/graph_model";
import { _t } from "@web/core/l10n/translation";

export class ProjectTaskGraphModel extends GraphModel {
    _getDefaultFilterLabel(field) {
        if (field.fieldName === "project_id") {
            return _t("🔒 Private");
        }
        return super._getDefaultFilterLabel(field);
    }
}
