/** @odoo-module */
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanEditorRecordLegacy } from "@web_studio/client_action/view_editor/editors/kanban_legacy/kanban_editor_record_legacy";
import { useRef, useEffect } from "@odoo/owl";

export class KanbanEditorRendererLegacy extends kanbanView.Renderer {
    static template = "web_studio.KanbanEditorRendererLegacy";
    static components = {
        ...kanbanView.Renderer.components,
        KanbanRecord: KanbanEditorRecordLegacy,
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
                el.classList.add("o_web_studio_kanban_view_editor_legacy");
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
