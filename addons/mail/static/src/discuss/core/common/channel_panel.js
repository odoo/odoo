import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Typing } from "@mail/discuss/typing/common/typing";

import { Component, proxy, signal, t, useProps } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled } from "@web/core/utils/misc";

/**
 * Action panel displaying the thread and composer of a channel, within the context (thread actions,
 * message highlight, ...) of its host, e.g. a meeting or a side channel.
 */
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
        this.ancestors = useAncestors({ inChannelPanel: true });
    }

    get channel() {
        return this.props.channel;
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        if (getActiveHotkey(ev) !== "escape") {
            return;
        }
        // Escape within the panel belongs to the panel
        ev.stopPropagation();
        if (isEventHandled(ev, "NavigableList.close")) {
            return;
        }
        if (this.channel.composer.replyToMessage) {
            this.channel.composer.replyToMessage = undefined;
        } else {
            this.props.close();
        }
    }

    get pinnedMessagesAction() {
        return this.ancestors.threadActions?.get("pinned-messages");
    }
}
