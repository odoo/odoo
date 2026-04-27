import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { KanbanEditorRecord } from "@web_studio/client_action/view_editor/editors/kanban/kanban_editor_record";
import { useRef, useEffect } from "@odoo/owl";

class KanbanEditorHeader extends KanbanHeader {
    static template = "web_studio.KanbanEditorHeader";
}

export class KanbanEditorRenderer extends kanbanView.Renderer {
    static template = "web_studio.KanbanEditorRenderer";
    static components = {
        ...kanbanView.Renderer.components,
        KanbanRecord: KanbanEditorRecord,
        KanbanHeader: KanbanEditorHeader,
    };

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
