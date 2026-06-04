import { patch } from "@web/core/utils/patch";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { onMounted } from "@odoo/owl";

patch(BottomSheet, {
    props: {
        ...BottomSheet.props,
        withUnfocus: { type: Boolean, optional: true },
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
