import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

export class MailComposerPlugin extends Plugin {
    static id = "mail.composer";
    static dependencies = ["hint"];
    resources = {
        hints: [
            withSequence(1, {
                selector: `.odoo-editor-editable > ${baseContainerGlobalSelector}:only-child`,
                text: this.config.placeholder,
            }),
        ],
        hint_targets_providers: (selectionData, editable) => {
            const el = editable.firstChild;
            if (
                !selectionData.documentSelectionIsInEditable &&
                childNodes(editable).length === 1 &&
                isEmptyBlock(el) &&
                el.matches(baseContainerGlobalSelector)
            ) {
                return [el];
            } else {
                return [];
            }
        },
    };

    setup() {
        this.addDomListener(
            this.editable,
            "keydown",
            this.config.composerPluginDependencies.onKeydown
        );
    }
}
