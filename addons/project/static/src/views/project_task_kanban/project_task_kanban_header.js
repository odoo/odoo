/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from '@web/core/utils/hooks';
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { onWillStart } from "@odoo/owl";

export class ProjectTaskKanbanHeader extends KanbanHeader {
    setup() {
        super.setup();
        this.action = useService('action');

        this.isProjectManager = false;
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        if (this.props.list.isGroupedByStage) { // no need to check it if not grouped by stage
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        }
    }

    async deleteGroup() {
        return this.props.deleteGroup(this.group);
    }

    canEditGroup(group) {
        return super.canEditGroup(group) && (!this.props.list.isGroupedByStage || this.isProjectManager);
    }

    canDeleteGroup(group) {
        return super.canDeleteGroup(group) && (!this.props.list.isGroupedByStage || this.isProjectManager);
    }

    /**
     * @override
     */
    _getEmptyGroupLabel(fieldName) {
        if (fieldName === "project_id") {
            return _t("🔒 Private");
        } else if (fieldName === "user_ids") {
            return _t("👤 Unassigned");
        } else {
            return super._getEmptyGroupLabel(fieldName);
        }
    }
}
