import { AttachmentList } from "@mail/core/common/attachment_list";
import { MessageBodyContent } from "@mail/core/common/message_body_content";
import { ChannelActionDialog } from "@mail/discuss/core/common/channel_action_dialog";
import { DiscussSelectableList } from "@mail/discuss/core/common/selectable_list";
import { compareDatetime } from "@mail/utils/common/misc";

import { Component, onWillStart, props, proxy, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { useDebounced } from "@web/core/utils/timing";

const SEARCH_LIMIT = 15;

function toItem(type, record) {
    return {
        key: `${type}-${record.id}`,
        label: record.displayName,
        avatarRecord: record,
        type,
        record,
    };
}

export function openForwardDialog(env, message) {
    env.services.dialog.add(ChannelActionDialog, {
        contentClass: "o-discuss-ChannelInvitation o-mail-ForwardDialog",
        contentComponent: ForwardDialog,
        contentProps: {
            close: () => env.services.dialog.closeAll(),
            message,
        },
        title: _t("Forward To"),
    });
}

export class ForwardDialog extends Component {
    static components = { AttachmentList, DiscussSelectableList, MessageBodyContent };
    static template = "mail.ForwardDialog";
    static SEARCH_LIMIT = SEARCH_LIMIT;
    static MAX_SELECTIONS = 5;

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.notification = useService("notification");
        this.props = props({
            close: t.function([]).optional(),
            message: t.instanceOf(this.store["mail.message"].Class),
        });
        this.state = proxy({
            isSending: false,
            optionalMessage: "",
            searchStr: "",
            selectedDestinations: [],
        });
        this.searchConversations = useDebounced(
            () => this.store.searchConversations(this.state.searchStr.trim()),
            250
        );
        this.resultNarrowText = _t(
            "Showing the first %(search_limit)s results. Narrow your search to see more choices.",
            { search_limit: SEARCH_LIMIT }
        );
        onWillStart(() => this.store.searchConversations(""));
    }

    get search() {
        return {
            inputId: "o-mail-ForwardDialog-search",
            onInput: (value) => {
                this.state.searchStr = value;
                this.searchConversations();
            },
            placeholder: _t("Search conversations"),
            value: this.state.searchStr,
        };
    }

    get selectableItems() {
        const term = this.state.searchStr.trim();
        const termLower = term.toLowerCase();
        const source = this.props.message.channel_id;
        const channels = Object.values(this.store["discuss.channel"].records)
            .filter(
                (channel) =>
                    channel?.self_member_id &&
                    !channel.eq(source) &&
                    this.isDestinationAllowed(channel) &&
                    (!termLower || channel.displayName?.toLowerCase().includes(termLower))
            )
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id)
            .map((channel) => toItem("channel", channel));
        const partners = Object.values(this.store["res.partner"].records).filter(
            (partner) =>
                partner?.id &&
                partner.notEq(this.store.self_user?.partner_id) &&
                partner.searchChat() === undefined
        );
        const matchedPartners = (
            term ? fuzzyLookup(term, partners, (partner) => partner.displayName) : partners
        ).map((partner) => toItem("partner", partner));
        return [...channels, ...matchedPartners].slice(0, SEARCH_LIMIT);
    }

    /** Overridden by livechat to exclude ended conversations. */
    isDestinationAllowed(channel) {
        return true;
    }

    onToggle(item) {
        const { selectedDestinations } = this.state;
        const index = selectedDestinations.findIndex((d) => d.key === item.key);
        if (index === -1) {
            selectedDestinations.push(item);
        } else {
            selectedDestinations.splice(index, 1);
        }
    }

    async onClickSend() {
        const { selectedDestinations, optionalMessage, isSending } = this.state;
        if (!selectedDestinations.length || isSending) {
            return;
        }
        this.state.isSending = true;
        try {
            const target_channels_ids = [];
            for (const { type, record } of selectedDestinations) {
                if (type === "channel") {
                    target_channels_ids.push(record.id);
                } else {
                    const chat = await this.store.joinChat(record.id);
                    if (chat) {
                        target_channels_ids.push(chat.id);
                    }
                }
            }
            const optional_msg_body = optionalMessage.trim() || false;
            await rpc("/mail/message/forward", {
                forwarded_from_id: this.props.message.id,
                target_channels_ids,
                optional_msg_body,
                optional_msg_has_link: optional_msg_body && /https?:\/\//i.test(optional_msg_body),
                source_msg_has_link: this.props.message.hasLink,
            });
            this.props.close?.();
            const others = target_channels_ids.filter(
                (id) => id !== this.props.message.channel_id?.id
            );
            if (others.length === 1) {
                this.store["discuss.channel"].get(others[0])?.open({ focus: true });
            } else {
                this.notification.add(_t("Message forwarded"), { type: "success" });
            }
        } finally {
            this.state.isSending = false;
        }
    }
}
