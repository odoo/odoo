import { MessageCardList } from "@mail/core/common/message_card_list";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, t, useOnChange, usePlugin, useProps } from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class PinnedMessagesPanel extends Component {
    static components = {
        MessageCardList,
        ActionPanel,
    };
    static template = "discuss.PinnedMessagesPanel";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.offlinePlugin = usePlugin(OfflinePlugin);
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]),
            close: t.function([t.instanceOf(MouseEvent)]).optional(),
        });
        useOnChange(
            () => [this.props.channel],
            (channel) => channel.fetchPinnedMessages()
        );
    }

    /**
     * Get the message to display when nothing is pinned on this channel or client is offline.
     */
    get emptyText() {
        if (this.offlinePlugin.isOffline() && this.props.channel.pinnedMessagesState !== "loaded") {
            return _t("Go online to load pinned messages.");
        }
        return _t("This channel doesn't have any pinned messages.");
    }
}
