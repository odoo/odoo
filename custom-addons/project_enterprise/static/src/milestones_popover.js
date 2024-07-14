/** @odoo-module **/

import { Component } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";

export class MilestonesPopover extends Component {
    getDeadline(milestone) {
        if (!milestone.deadline) {
            return;
        }
        return formatDate(milestone.deadline);
    }
}

MilestonesPopover.template = "project_enterprise.MilestonesPopover";
MilestonesPopover.props = ["close", "displayMilestoneDates", "displayProjectName", "milestones"];
