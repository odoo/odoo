/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Dropdown } from "@web/core/dropdown/dropdown";

patch(Dropdown.prototype, {
    /**
     * Embedded views in knowledge can become the active element,
     * but dropdowns should be able to be closed by clicking.
     * This override is necessary because dropdowns mounted inside an
     * embedded view register the document as their active element instead
     * of the embedded view itself.
     *
     * @override
     */
    popoverCloseOnClickAway(target, activeEl) {
        const currentActiveEl = this.uiService.getActiveElementOf(target);
        return (
            super.popoverCloseOnClickAway(target, activeEl) ||
            (currentActiveEl !== activeEl &&
                activeEl &&
                activeEl.contains(currentActiveEl) &&
                currentActiveEl.dataset.embedded)
        );
    },
});
