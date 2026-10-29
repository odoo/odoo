import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ChannelPanel } from "@mail/discuss/core/common/channel_panel";

import { Component, providePlugins, t, useOnChange, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/** Sub-channel shown beside its parent in the Discuss app, @see DiscussApp.sideChannel */
export class DiscussSideChannel extends Component {
    static template = "mail.DiscussSideChannel";
    static components = { ChannelPanel };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]),
            close: t.function(),
            openInFullView: t.function(),
        });
        this.threadActions = useThreadActions({ thread: () => this.props.channel.thread });
        providePlugins([MessageHighlightPlugin], { thread: () => this.props.channel.thread });
        useOnChange(
            () => [this.threadActions.panelAction],
            (panelAction) => panelAction && this.props.openInFullView(panelAction),
            { initialRun: false }
        );
    }

    /** Hands focus back to the parent composer, as nothing else takes it when closed from within. */
    close() {
        this.props.close();
        this.props.channel.parent_channel_id.thread.composer.autofocus++;
    }
}
