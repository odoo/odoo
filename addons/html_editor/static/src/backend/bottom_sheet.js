import { patch } from "@web/core/utils/patch";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { onMounted } from "@odoo/owl";
import { useViewportChange } from "@web/core/utils/dvu";

patch(BottomSheet, {
    props: {
        ...BottomSheet.props,
        withUnfocus: { type: Boolean, optional: true },
        fitOnResize: { type: Boolean, optional: true },
    },
});

patch(BottomSheet.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            if (this.props.withUnfocus) {
                this.sheetRef.el.ownerDocument.activeElement?.blur();
            }
        });
        // Adapt dimensions when mobile virtual-keyboards or browsers bars toggle
        if (this.props.fitOnResize) {
            useViewportChange(() => {
                if (this.state.isPositionedReady && !this.state.isDismissing) {
                    this.updateProgressValue(0);
                }
            });
        }
    },

    onIframeLoad(ev) {
        const doc = this.sheetRef.el.ownerDocument;
        if (doc.hasFocus() && !doc.getSelection().isCollapsed) {
            // Hide mobile text selection widgets by focusing something else
            // without losing in-document selection.
            const iframeDoc = ev.target.contentDocument;
            if (!iframeDoc.hasFocus()) {
                const inputEl = iframeDoc.querySelector("input");
                inputEl.focus();
                // Somehow this does not display the keyboard - which is what we want.
                // If we disable the field, some phones keep displaying the selection widgets.
            }
        }
    },
});
