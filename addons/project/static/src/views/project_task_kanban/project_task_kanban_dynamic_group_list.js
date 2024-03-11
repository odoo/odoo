/** @odoo-module */

import { KanbanDynamicGroupList } from "@web/views/kanban/kanban_model";
import { Domain } from '@web/core/domain';
import { session } from '@web/session';

export class ProjectTaskKanbanDynamicGroupList extends KanbanDynamicGroupList {
    get context() {
        const context = super.context;
        if (context.createPersonalStageGroup) {
            context.default_user_id = context.uid;
            delete context.createPersonalStageGroup;
            delete context.default_project_id;
        }
        return context;
    }

    get isGroupedByStage() {
        return !!this.groupByField && this.groupByField.name === 'stage_id';
    }

    get isGroupedByPersonalStages() {
        return !!this.groupByField && this.groupByField.name === 'personal_stage_type_ids';
    }

    async _loadGroups() {
        if (!this.isGroupedByPersonalStages) {
            return super._loadGroups(...arguments);
        }
        const previousDomain = this.domain;
        this.domain = Domain.and([[['user_ids', 'in', session.uid]], previousDomain]).toList({});
        const result = await super._loadGroups(...arguments);
        this.domain = previousDomain;
        return result;
    }

    async createGroup() {
        if (this.isGroupedByPersonalStages) {
            this.defaultContext = Object.assign({}, this.defaultContext || {}, {
                createPersonalStageGroup: true,
            });
        }
        const result = await super.createGroup(...arguments);
        if (this.isGroupedByPersonalStages) {
            delete this.defaultContext.createPersonalStageGroup;
        }
        return result;
    }
}
