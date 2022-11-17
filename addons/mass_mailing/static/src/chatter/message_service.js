/* @odoo-module */

import { patch } from "@web/core/utils/patch";

import { MessageService } from "@mail/core/common/message_service";
import { MailingTrace } from "./mailing_trace_model";


patch(MessageService.prototype, "mass_mailing", {
    insert(data) {
        const message = this._super(data);
        if (!data.traces) {
            data.traces = [];
        }
        message.traces = data.traces.map(trace => new MailingTrace(trace));
        return message;
    },
});
