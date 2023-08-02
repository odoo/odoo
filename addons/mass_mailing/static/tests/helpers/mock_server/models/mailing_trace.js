/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mass_mailing/models/mailing_trace', {
    /**
     * @param {Integer[]} ids corresponsing to the mailing traces of a message
     * @returns {Object[]} list of formatted traces
     */
    _mockMailingTraceFormat(ids) {
        const traces = this.getRecords('mailing.trace', [['id', 'in', ids]]);
        return traces.map(trace => {
            return {
                id: trace.id,
                email: trace.email,
                trace_type: trace.trace_type,
                trace_status: trace.trace_status,
                failure_type: trace.failure_type,
                mailing_id: trace.mass_mailing_id,
            };
        });
    },
});
