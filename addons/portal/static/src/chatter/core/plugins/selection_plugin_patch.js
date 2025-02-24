import { SelectionPlugin } from "@html_editor/core/selection_plugin";

import { patch } from "@web/core/utils/patch";

patch(SelectionPlugin.prototype, {
    /**
     * @return { Selection }
     */
    getSelection() {
        const root = this.editable.getRootNode();
        return this.editable.classList.contains("o-mail-Composer-input-portal") &&
            root instanceof ShadowRoot
            ? root.getSelection()
            : super.getSelection();
    },
});
