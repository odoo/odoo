/** @odoo-module */
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanEditorRecord } from "@web_studio/client_action/view_editor/editors/kanban/kanban_editor_record";
import { useRef, useEffect } from "@odoo/owl";

export class KanbanEditorRenderer extends kanbanView.Renderer {
    setup() {
        super.setup();
        const rootRef = useRef("root");
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                el.classList.add("o_web_studio_kanban_view_editor");
            },
            () => [rootRef.el]
        );
    }

    get canUseSortable() {
        return false;
    }

    get showNoContentHelper() {
        return false;
    }

    getGroupsOrRecords() {
        const { list } = this.props;
        const groupsOrRec = super.getGroupsOrRecords(...arguments);
        if (list.isGrouped) {
            return [groupsOrRec.filter((el) => el.group.list.records.length)[0]];
        } else {
            return [groupsOrRec[0]];
        }
    }

    canCreateGroup() {
        return false;
    }

    getGroupUnloadedCount() {
        return 0;
    }
}
KanbanEditorRenderer.template = "web_studio.KanbanEditorRenderer";
KanbanEditorRenderer.components = {
    ...kanbanView.Renderer.components,
    KanbanRecord: KanbanEditorRecord,
};
