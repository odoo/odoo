/** @odoo-module */

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { patch } from "@web/core/utils/patch";

patch(DomainSelector.prototype, {
    /**
     * Hides the 'Include Archived' checkbox from the domain selector for 'documents' model
     * since it is no longer relevant.
     *
     * @override
     */
    getShowArchivedCheckBox(_, props) {
        if (props.resModel === "documents.document") {
            return false;
        }
        return super.getShowArchivedCheckBox(...arguments);
    },
});
