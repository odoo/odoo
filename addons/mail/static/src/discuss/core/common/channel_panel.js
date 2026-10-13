import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { Composer } from "@mail/core/common/composer";
import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";
import { Thread } from "@mail/core/common/thread";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useMaybePlugin } from "@mail/utils/common/hooks";

import { Component, providePlugins, proxy, signal, t, useProps } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

/** Action panel displaying the thread and composer of a channel. */
export class ChannelPanel extends Component {
    static template = "mail.ChannelPanel";
    static components = { ActionPanel, Composer, Thread, Typing };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]),
            close: t.function(),
            title: t.string(),
        });
        this.state = proxy({ jumpPresent: 0 });
        this.panelContentRef = signal.ref();
        this.isMobileOS = isMobileOS();
        useAncestors({ inChannelPanel: true });
        // reuse the parent's one if any, so that its other children can highlight messages here
        if (!useMaybePlugin(MessageHighlightPlugin)) {
            providePlugins([MessageHighlightPlugin], { thread: () => this.channel.thread });
        }
    }

    get channel() {
        return this.props.channel;
    }
}
