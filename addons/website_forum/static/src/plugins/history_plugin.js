import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { withSequence } from "@html_editor/utils/resource";

export class ForumHistoryPlugin extends HistoryPlugin {
    resources = {
        ...this.resources,
        // Undo and redo toolbar buttons are always available
        toolbar_groups: withSequence(5, { id: "history", namespaces: ["compact", "expanded"] }),
        toolbar_items: [
            {
                id: "undo",
                groupId: "history",
                commandId: "historyUndo",
                isDisabled: () => !this.canUndo(),
            },
            {
                id: "redo",
                groupId: "history",
                commandId: "historyRedo",
                isDisabled: () => !this.canRedo(),
            },
        ],
    };
}
