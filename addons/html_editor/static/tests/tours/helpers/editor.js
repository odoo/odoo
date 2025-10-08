import { patch } from "@web/core/utils/patch";

// To expose the editor instance globally for tour.
export const editorsWeakMap = new WeakMap();

const editorModule = odoo.loader.modules.get("@html_editor/editor");
if (editorModule) {
    const { Editor } = editorModule;
    patch(Editor.prototype, {
        attachTo(editable) {
            editorsWeakMap.set(editable.ownerDocument, this);
            return super.attachTo(...arguments);
        },
    });
}

export function setSelection({
    anchorNode,
    anchorOffset,
    focusNode = anchorNode,
    focusOffset = anchorOffset,
}) {
    const selection = anchorNode.ownerDocument.getSelection();
    selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
}
