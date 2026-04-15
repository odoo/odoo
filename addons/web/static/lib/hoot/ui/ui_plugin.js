/** @odoo-module */

import { computed, Plugin, signal, types as t } from "@odoo/owl";
import { T_NULL } from "../hoot_utils";

export class UiPlugin extends Plugin {
    /** @private */
    _statusFilter = signal(null, {
        type: t.selection(["failed", "passed", "skipped", "todo", null]),
    });

    resultsPage = signal(0, { type: t.number() });
    resultsPerPage = signal(40, { type: t.number() });
    selectedSuiteId = signal(null, { type: t.or([t.string(), T_NULL]) });
    sortResults = signal(false, { type: t.selection(["asc", "desc", false]) });
    totalResults = signal(0, { type: t.number() });

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
