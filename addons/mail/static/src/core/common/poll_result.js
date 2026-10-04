import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";
import { useMaybePlugin } from "@mail/utils/common/hooks";

import { Component, types, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class PollResult extends Component {
    static template = "mail.PollResult";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            poll: types.instanceOf(this.store["mail.poll"]),
        });
        this.messageHighlight = useMaybePlugin(MessageHighlightPlugin);
    }

    onClickViewPoll() {
        this.messageHighlight?.highlightMessage(this.props.poll.start_message_id);
    }
}
