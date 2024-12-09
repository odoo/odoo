import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { hasTouch } from "@web/core/browser/feature_detection";

export class MobilePlugin extends Plugin {
    static id = "mobile";
    static dependencies = ["history"];
    resources = {
        ...(hasTouch() && {
            toolbar_groups: withSequence(5, { id: "historyMobile" }),
            toolbar_items: [
                {
                    id: "undo",
                    groupId: "historyMobile",
                    commandId: "historyUndo",
                    isDisabled: () => !this.dependencies.history.canUndo(),
                },
                {
                    id: "redo",
                    groupId: "historyMobile",
                    commandId: "historyRedo",
                    isDisabled: () => !this.dependencies.history.canRedo(),
                },
            ],
        }),
    };
}
