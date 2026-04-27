import { Plugin } from "@html_editor/plugin";
import { paragraphRelatedElementsSelector } from "@html_editor/utils/dom_info";

export class AutofocusPlugin extends Plugin {
    static id = "autofocus";
    static dependencies = ["selection"];
    resources = {
        start_edition_handlers: this.focusFirstElement.bind(this),
    };

    focusFirstElement() {
        for (const paragraph of this.editable.querySelectorAll(paragraphRelatedElementsSelector)) {
            if (paragraph.isContentEditable) {
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    this.dependencies.selection.setSelection({
                        anchorNode: paragraph,
                        anchorOffset: 0,
                    });
                const selectionData = this.dependencies.selection.getSelectionData();
                if (!selectionData.documentSelectionIsInEditable) {
                    const selection = this.document.getSelection();
                    selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
                }
                break;
            }
        }
    }
}
