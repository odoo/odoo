import { KanbanRenderer, kanbanRendererProps } from '@web/views/kanban/kanban_renderer';
import { ProjectTaskColumnQuickCreate } from './project_task_column_quick_create';
import { ProjectTaskKanbanRecord } from './project_task_kanban_record';
import { ProjectTaskKanbanHeader } from './project_task_kanban_header';
import { useService } from '@web/core/utils/hooks';
import { onWillStart, useListener, useProps, t } from "@odoo/owl";
import { user } from "@web/core/user";
import { pointerState } from "@web_tour/js/tour_pointer/tour_pointer";


export class ProjectTaskKanbanRenderer extends KanbanRenderer {
    static template = "project.ProjectTaskKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: ProjectTaskKanbanRecord,
        KanbanHeader: ProjectTaskKanbanHeader,
        ProjectTaskColumnQuickCreate,
    };

    props = useProps({ ...kanbanRendererProps, hideKanbanStagesNocontent: t.any().optional() });

    setup() {
        super.setup();
        this.action = useService('action');
        this.nextStageGroup = null;

        useListener(this.rootRef, "pointerover", this.onRecordPointerOver.bind(this));
        useListener(this.rootRef, "pointerleave", () => this.highlightNextStage(null));

        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        });
    }

    canCreateGroup() {
        // This restrict the creation of project stages to the kanban view of a given project
        return (
            super.canCreateGroup() &&
            ((!!this.props.list.context.default_project_id == this.props.list.isGroupedByStage &&
                this.isProjectManager) ||
                this.props.list.groupByField.name === "personal_stage_type_id")
        );
    }

    /**
     * Next unfolded-or-folded stage column on the right, if any.
     *
     * @param {HTMLElement} groupEl
     * @returns {HTMLElement|null}
     */
    getNextStageEl(groupEl) {
        let el = groupEl.nextElementSibling;
        while (el && !el.classList.contains("o_kanban_group")) {
            el = el.nextElementSibling;
        }
        return el;
    }

    highlightNextStage(group) {
        if (this.nextStageGroup === group) {
            return;
        }
        this.nextStageGroup?.classList.remove("o_kanban_next_stage");
        this.nextStageGroup = group;
        group?.classList.add("o_kanban_next_stage");
    }

    onRecordPointerOver(ev) {
        if (ev.pointerType !== "mouse") {
            return;
        }
        const cardEl = ev.target.closest?.(".o_kanban_record");
        if (
            !cardEl ||
            pointerState.stepId !== "drag_task_to_next_stage" ||
            cardEl !== pointerState.trigger ||
            this.rootRef()?.querySelector(".o_dragged")
        ) {
            // highligh only when hovering on the card that is pointed at
            // when the tour is running in the drag step and no card is being dragged
            this.highlightNextStage(null);
            return;
        }
        const groupEl = cardEl.closest(".o_kanban_group");
        this.highlightNextStage(groupEl && this.getNextStageEl(groupEl));
    }
}
