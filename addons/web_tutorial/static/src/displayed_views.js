import { onWillDestroy } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { View } from "@web/views/view";

/**
 * A view displayed in the web client
 * @typedef DisplayedView
 * @property {Object} [context]
 * @property {string} resModel
 * @property {string} type e.g. "form"
 */

/**
 * The outermost view of each dialog, by id of the dialog (its DOM doesn't
 * tell the model of its view, and it may not be an action)
 * @type {Map<string, () => DisplayedView>}
 */
export const dialogViews = new Map();

patch(View.prototype, {
    /** Tracks the outermost view of its dialog, not the views it embeds */
    setup() {
        super.setup();
        const { dialogId } = this.env;
        if (!dialogId || dialogViews.has(dialogId)) {
            return;
        }
        const getView = () => {
            const { context, resModel, type } = this.props();
            return { context, resModel, type };
        };
        dialogViews.set(dialogId, getView);
        onWillDestroy(() => {
            if (dialogViews.get(dialogId) === getView) {
                dialogViews.delete(dialogId);
            }
        });
    },
});
