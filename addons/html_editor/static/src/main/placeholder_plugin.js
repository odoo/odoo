import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { Plugin } from "../plugin";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { withSequence } from "@html_editor/utils/resource";

export class PlaceholderPlugin extends Plugin {
    static id = "placeholder";
    resources = {
        ...(this.config.placeholder && {
            hints: [
                withSequence(1, {
                    selector: `.odoo-editor-editable > ${baseContainerGlobalSelector}:only-child`,
                    text: this.config.placeholder,
                }),
            ],
            hint_targets_providers: (selectionData, editable) => {
                if (
                    selectionData.documentSelectionIsInEditable ||
                    childNodes(editable).length !== 1
                ) {
                    return [];
                }
                const el = editable.firstChild;
                if (isEmptyBlock(el) && el.matches(baseContainerGlobalSelector)) {
                    return [el];
                }
                return [];
            },
        }),
    };
}
