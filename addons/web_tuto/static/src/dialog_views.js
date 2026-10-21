import { onWillDestroy } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { View } from "@web/views/view";

/**
 * The props of the view displayed in each dialog, by id of the dialog: the
 * DOM of a dialog doesn't tell the model of its view. Only the outermost view
 * of a dialog is kept, not the ones it may embed (e.g. the list of a x2many
 * field of its form).
 * @type {Map<string, () => Object>}
 */
export const dialogViewProps = new Map();

patch(View.prototype, {
    setup() {
        super.setup();
        const { dialogId } = this.env;
        if (dialogId && !dialogViewProps.has(dialogId)) {
            const getProps = () => this.props();
            dialogViewProps.set(dialogId, getProps);
            onWillDestroy(() => {
                if (dialogViewProps.get(dialogId) === getProps) {
                    dialogViewProps.delete(dialogId);
                }
            });
        }
    },
});
