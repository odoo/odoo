/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Dropdown } from "@web/core/dropdown/dropdown";


patch(Dropdown.prototype, {
    /**
     * Embedded view in knowledge can become the active element,
     * but dropdowns should be able to be closed by clicking.
     * Actually, the only case where a dropdown should sometimes not be closed is if
     * a dialog becomes the active element above the opened dropdown.
     * @override
     */
    isInActiveElement() {
        return (
            super.isInActiveElement() ||
            (
                this.ui.activeElement !== this.myActiveEl &&
                this.myActiveEl &&
                this.myActiveEl.contains(this.ui.activeElement) &&
                this.ui.activeElement.classList.contains("o_knowledge_behavior_anchor")
            )
        );
    },
});
