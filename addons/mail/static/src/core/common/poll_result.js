import { propComputed } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class PollResult extends Component {
    static template = "mail.PollResult";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.poll = propComputed("poll", t.instanceOf(this.store["mail.poll"]));
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ pollAtRender: import("models").MailPollModel }} param1
     */
    onClickViewPoll(ev, { pollAtRender }) {
        this.env.messageHighlight.highlightMessage(
            pollAtRender.start_message_id,
            pollAtRender.start_message_id.thread
        );
    }
}
