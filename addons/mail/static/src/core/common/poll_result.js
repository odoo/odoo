import { Component, types, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class PollResult extends Component {
    static template = "mail.PollResult";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            poll: types.instanceOf(this.store["mail.poll"].Class),
        });
    }

    onClickViewPoll() {
        this.env.messageHighlight.highlightMessage(
            this.props.poll.start_message_id,
            this.props.poll.start_message_id.thread
        );
    }
}
