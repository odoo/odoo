/** @odoo-module **/
import { dragAndDropHelper } from "@web_editor/js/editor/drag_and_drop";

export class dragAndDropHelperWebsite extends dragAndDropHelper {
    /**
     * Changes some behaviors before the drag and drop.
     *
     * @private
     * @override
     * @returns {Function} a function that restores what was changed when the
     *  drag and drop is over.
     */
    prepareDrag() {
        const restore = super.prepareDrag();
        // Remove the footer scroll effect if it has one (because the footer
        // dropzone flickers otherwise when it is in grid mode).
        const wrapwrapEl = this.bodyEl.ownerDocument.defaultView.document.body.querySelector("#wrapwrap");
        const hasFooterScrollEffect = wrapwrapEl && wrapwrapEl.classList.contains("o_footer_effect_enable");
        if (hasFooterScrollEffect) {
            wrapwrapEl.classList.remove("o_footer_effect_enable");
            return () => {
                wrapwrapEl.classList.add("o_footer_effect_enable");
                restore();
            };
        }
        return restore;
    }
}
