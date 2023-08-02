/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

// ensure load order
import "@mail/../tests/helpers/mock_server/models/mail_message";

patch(MockServer.prototype, 'mass_mailing/models/mail_message', {
    /**
     * @override
     */
    _mockMailMessageMessageFormat(ids) {
        const response = this._super(ids);
        for (const formattedMessage of response) {
            const message = this.getRecords('mail.message', [['id', '=', formattedMessage.id]])[0];
            const traces = this.getRecords('mailing.trace', [['mail_message_id', '=', message.id]]);
            const formattedTraces = this._mockMailingTraceFormat(traces.map(trace => trace.id));

            formattedMessage.traces = formattedTraces;
        }
        return response;
    },
});
