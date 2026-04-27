/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ListRenderer } from "@web/views/list/list_renderer";

export class HelpdeskTicketListRenderer extends ListRenderer {
    getGroupDisplayName(group) {
        if (group.groupByField.name === "sla_deadline" && !group.value) {
            return _t("Deadline reached");
        } else {
            return super.getGroupDisplayName(group);
        }
    }
}
