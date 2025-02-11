/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Picker } from "@mail/core/common/picker";
import { isEventHandled } from "@web/core/utils/misc";

patch(Picker.prototype, {
    /**
     * @param {Event} ev
     * @returns {boolean}
     */
    isEventHandledByPicker(ev) {
        return super.isEventHandledByPicker(ev) || isEventHandled(ev, "Composer.onClickAddGif");
    },
    async toggle(el, ev) {
        // Let event be handled by bubbling handlers first.
        await super.toggle(el, ev);
        if (isEventHandled(ev, "Composer.onClickAddGif")) {
            if (this.popover.isOpen) {
                if (this.props.state.picker === this.props.PICKERS.GIF) {
                    this.close();
                    return;
                }
                this.props.state.picker = this.props.PICKERS.GIF;
            } else {
                this.props.state.picker = this.props.PICKERS.GIF;
                this.popover.open(el, this.contentProps);
            }
        }
    },
});
