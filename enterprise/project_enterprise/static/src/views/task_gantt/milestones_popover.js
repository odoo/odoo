/** @odoo-module **/

import { Component } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";

export class MilestonesPopover extends Component {
    static template = "project_enterprise.MilestonesPopover";
    static props = ["close", "displayMilestoneDates", "displayProjectName", "projects"];

    getDeadline(milestone) {
        if (!milestone.deadline) {
            return;
        }
        return formatDate(milestone.deadline);
    }
}
