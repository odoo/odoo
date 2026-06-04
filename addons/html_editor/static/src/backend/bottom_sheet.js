import { patch } from "@web/core/utils/patch";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { onMounted, t, useProps } from "@odoo/owl";

patch(BottomSheet.prototype, {
    setup() {
        super.setup();
        this.htmlEditorProps = useProps({
            withUnfocus: t.boolean().optional(false),
        });
        onMounted(() => {
            if (this.htmlEditorProps.withUnfocus) {
                this.sheetRef().ownerDocument.activeElement?.blur();
            }
        });
    },

    onIframeLoad(ev) {
        const doc = this.sheetRef().ownerDocument;
        if (doc.hasFocus() && !doc.getSelection().isCollapsed) {
            // Hide mobile text selection widgets by focusing something else
            // without losing in-document selection.
            const iframeDoc = ev.target.contentDocument;
            if (!iframeDoc.hasFocus()) {
                const defaultActiveElement = doc.activeElement;
                const inputEl = iframeDoc.querySelector("input");
                inputEl.focus();
                // Somehow this does not display the keyboard - which is what we want.
                // If we disable the field, some phones keep displaying the selection widgets.
                if (defaultActiveElement) {
                    // But we need to restore the actual default focused element.
                    defaultActiveElement.focus();
                    inputEl.remove();
                }
            }
        }
    },
});
