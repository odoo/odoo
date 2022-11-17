/* @odoo-module */

import { markEventHandled } from "@web/core/utils/misc";
import { patch } from "@web/core/utils/patch";

import { Message } from "@mail/core/common/message";


patch(Message.prototype, "mass_mailing", {
    onClickFailure(ev) {
        if (this.message.failureTraces.length > 0) {
            markEventHandled(ev, 'Message.ClickFailure');
            this.openMailingView();
            return;
        }
        this._super(ev);
    },
    /**
     * Opens the mailing the message originated from.
     */
    openMailingView() {
        this.messaging.openDocument({ id: this.message.failureTraces[0].mailing_id, model: 'mailing.mailing' });
    },
});
