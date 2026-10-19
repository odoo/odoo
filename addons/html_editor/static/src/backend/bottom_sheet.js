import { patch } from "@web/core/utils/patch";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { t, useProps } from "@odoo/owl";
import { useViewportChange } from "@web/core/utils/dvu";

patch(BottomSheet.prototype, {
    setup() {
        super.setup();
        this.htmlEditorProps = useProps({
            withUnfocus: t.boolean().optional(false),
            fitOnResize: t.boolean().optional(false),
        });
        // Adapt dimensions when mobile virtual-keyboards or browsers bars toggle
        if (this.htmlEditorProps.fitOnResize) {
            useViewportChange(() => {
                setTimeout(() => {
                    if (this.state.isPositionedReady && !this.state.isDismissing) {
                        this.updateProgressValue(0);
                        // this.state.progress = 0;
                    }
                }, 1000);
            });
        }
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
                defaultActiveElement?.blur(); // For iOS
                inputEl.click(); // For iOS
                inputEl.focus(); // For Android
                // DO NOT SWAP ABOVE LINES
                // If we disable the field, some phones keep displaying the selection widgets.
                if (defaultActiveElement?.closest(".o_bottom_sheet")) {
                    // But we need to restore the actual default focused element.
                    defaultActiveElement.focus();
                    inputEl.remove();
                }
            }
        }
    },
});
