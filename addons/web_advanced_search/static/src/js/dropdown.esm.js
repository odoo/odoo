/** @odoo-module **/

import {Dropdown} from "@web/core/dropdown/dropdown";
import {patch} from "web.utils";

patch(Dropdown.prototype, "web.Dropdown", {
    /**
     * Our many2one widget in the filter menus has a dropdown that propagates some
     * custom events through the bus to the search more pop-up. This is not replicable
     * in core but we can simply cut it here
     * @override
     */
    onDropdownStateChanged(args) {
        const direct_siblings =
            args.emitter.rootRef.el.parentElement === this.rootRef.el.parentElement;
        if (!direct_siblings && args.emitter.myActiveEl !== this.myActiveEl) {
            return;
        }
        return this._super(...arguments);
    },
});
