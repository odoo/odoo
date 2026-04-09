/** @odoo-module */

import { computed, Plugin, signal, types as t } from "@odoo/owl";

export class UiPlugin extends Plugin {
    /** @private */
    _statusFilter = signal(null, {
        type: t.selection(["failed", "passed", "skipped", "todo", null]),
    });

    resultsPage = signal(0);
    resultsPerPage = signal(40);
    selectedSuiteId = signal(null, {
        type: t.or([t.string, t.literal(null)]),
    });
    sortResults = signal(false, {
        type: t.selection(["asc", "desc", false]),
    });
    totalResults = signal(0);

    statusFilter = computed(this._statusFilter, {
        set: (status) => {
            this.resultsPage.set(0);
            if (this._statusFilter() === status) {
                this._statusFilter.set(null);
            } else {
                this._statusFilter.set(status);
            }
        },
    });
}
