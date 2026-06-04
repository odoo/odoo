import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { MessageBodyContent } from "@mail/core/common/message_body_content";
import { SelectableList } from "@mail/discuss/core/common/selectable_list";
import { compareDatetime } from "@mail/utils/common/misc";
import { onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useDebounced } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";

const SEARCH_LIMIT = 10;

export class ForwardDialog extends SelectableList {
    static components = { AttachmentList, Dialog, DiscussAvatar, MessageBodyContent };
    static template = "mail.ForwardDialog";
    static props = {
        close: Function,
        message: Object,
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.notification = useService("notification");
        Object.assign(this.state, { optionalMessage: "", isSending: false });
        this.debouncedSearch = useDebounced(this.onSearchInput.bind(this), 300);
        onWillStart(() => this.store.searchConversations(""));
    }

    get sourceChannel() {
        return this.props.message.channel_id;
    }

    get emptyListText() {
        return _t("No destination found");
    }

    get searchPlaceholder() {
        return _t("Search conversations…");
    }

    get memberChannels() {
        const term = this.searchStr.trim().toLowerCase();
        return Object.values(this.store["discuss.channel"].records)
            .filter((channel) => {
                if (
                    !channel?.self_member_id ||
                    channel.id === this.sourceChannel?.id ||
                    channel.channel_type === "chat"
                ) {
                    return false;
                }
                if (term && !channel.displayName?.toLowerCase().includes(term)) {
                    return false;
                }
                return this.isDestinationAllowed(channel);
            })
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id)
            .slice(0, SEARCH_LIMIT);
    }

    get partnersWithoutChat() {
        const term = this.searchStr.trim();
        const recentChatPartnerIds = new Set(this.store.getRecentChatPartnerIds());
        const partners = Object.values(this.store["res.partner"].records).filter((partner) => {
            if (!partner?.id || recentChatPartnerIds.has(partner.id)) {
                return false;
            }
            return partner.searchChat() === undefined;
        });
        if (!term) {
            return partners.slice(0, SEARCH_LIMIT);
        }
        return fuzzyLookup(term, partners, (partner) => partner.displayName).slice(0, SEARCH_LIMIT);
    }

    /**
     * @param {import("models").DiscussChannel} channel
     */
    isDestinationAllowed(channel) {
        return true;
    }

    get selectableOptions() {
        const options = [];
        for (const channel of this.memberChannels) {
            options.push({
                key: `channel-${channel.id}`,
                label: channel.displayName,
                record: channel,
                type: "channel",
            });
        }
        for (const partner of this.partnersWithoutChat) {
            options.push({
                key: `partner-${partner.id}`,
                label: partner.displayName,
                record: partner,
                type: "partner",
            });
        }
        return options.slice(0, SEARCH_LIMIT);
    }

    async onSearchInput() {
        await this.store.searchConversations(this.searchStr.trim());
    }

    async resolveTargetChannelIds() {
        const channelIds = [];
        for (const key of this.selectedKeys) {
            const option = this.selectableOptions.find((o) => o.key === key);
            if (!option) {
                continue;
            }
            if (option.type === "channel") {
                channelIds.push(option.record.id);
            } else {
                const chat = await this.store.joinChat(option.record.id);
                if (chat) {
                    channelIds.push(chat.id);
                }
            }
        }
        return channelIds;
    }

    async onClickSend() {
        if (!this.canSend || this.state.isSending) {
            return;
        }
        this.state.isSending = true;
        const targetChannelIds = await this.resolveTargetChannelIds();
        const optionalMsgBody = this.state.optionalMessage.trim() || false;
        try {
            await rpc("/mail/message/forward", {
                forwarded_from_id: this.props.message.id,
                target_channels_ids: targetChannelIds,
                optional_msg_body: optionalMsgBody,
                optional_msg_has_link: optionalMsgBody && /https?:\/\//i.test(optionalMsgBody),
                source_msg_has_link: this.props.message.hasLink,
            });
        } finally {
            this.state.isSending = false;
        }
        this.props.close();
        const sourceChannelId = this.sourceChannel?.id;
        const newDestinations = targetChannelIds.filter((id) => id !== sourceChannelId);
        if (newDestinations.length === 1) {
            const channel = this.store["discuss.channel"].get(newDestinations[0]);
            channel?.open({ focus: true });
        } else {
            this.notification.add(_t("Message forwarded"), { type: "success" });
        }
    }
}
