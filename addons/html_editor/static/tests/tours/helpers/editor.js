import { patch } from "@web/core/utils/patch";
import { Editor } from "@html_editor/editor";

// To expose the editor instance globally for tour.
export const editorsWeakMap = new WeakMap();

patch(Editor.prototype, {
    attachTo(editable) {
        editorsWeakMap.set(editable.ownerDocument, this);
        return super.attachTo(...arguments);
    },
});
