import { propSignal } from "@mail/utils/common/hooks";

import { Component, providePlugins, proxy, signal, t } from "@odoo/owl";

import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { useService } from "@web/core/utils/hooks";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { Typing } from "@mail/discuss/typing/common/typing";
import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

export class DiscussSideChannel extends Component {
    static components = { ActionPanel, Composer, Thread, Typing };
    static template = "mail.DiscussSideChannel";

    setup() {
        super.setup();
        this.state = proxy({ jumpPresent: 0 });
        this.store = useService("mail.store");
        this.channel = propSignal("channel", t.instanceOf(this.store["discuss.channel"]));
        this.panelContentRef = signal.ref();
        providePlugins([MessageHighlightPlugin], { thread: () => this.thread });
        useAncestors({ inSideChannel: true });
    }
}
