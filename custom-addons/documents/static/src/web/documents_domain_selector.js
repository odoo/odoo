/** @odoo-module */

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { patch } from "@web/core/utils/patch";

patch(DomainSelector.prototype, {
    /**
     * Hides the 'Include Archived' checkbox from the domain selector for 'documents' model
     * since it is no longer relevant.
     *
     * @override
     * @param {string} resModel
     * @param {Set<string>} paths
     */
    async loadFieldDefs(resModel, paths) {
        await super.loadFieldDefs(resModel, paths);
        if (resModel === "documents.document") {
            if ("active" in this.fieldDefs) {
                delete this.fieldDefs.active;
            }
        }
    },
});
