import { SelectableList } from "@mail/discuss/core/common/selectable_list";
import { Gif } from "@mail/core/common/gif";

import { onWillStart, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useSequential } from "@mail/utils/common/hooks";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";
import { cleanTerm, prettifyMessageContent } from "@mail/utils/common/format";
import { compareDatetime } from "@mail/utils/common/misc";
import { url } from "@web/core/utils/urls";
import { createElementWithContent } from "@web/core/utils/html";

const MAX_FORWARD_SELECTION_LIMIT = 5;

export class ForwardDialog extends SelectableList {
    static components = {
        ...SelectableList.components,
        Dialog,
        Gif,
    };
    static props = ["sourceMessage", "close?"];
    static template = "mail.ForwardDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.sequential = useSequential();
        this.state = useState({
            selectableChannels: [],
            selectablePartners: [],
            optionalMsgBody: "",
        });
        this.debouncedFetchThreadsForForward = useDebounced(
            this.fetchThreadsForForward.bind(this),
            250
        );
        onWillStart(() => {
            if (this.store.self_user) {
                this.fetchThreadsForForward();
            }
        });
    }

    get maxSelectionLimit() {
        return MAX_FORWARD_SELECTION_LIMIT;
    }

    get subtitleText() {
        if (
            this.maxSelectionLimit &&
            this.internalState.selectedOptions.length >= this.maxSelectionLimit
        ) {
            return _t("You can only select up to %s items", this.maxSelectionLimit);
        }
        return _t("Select where you want to send this message.");
    }

    get options() {
        return this._buildOptions(this.state.selectableChannels, this.state.selectablePartners);
    }

    get selectedChannels() {
        return this.internalState.selectedOptions
            .filter((option) => option.isChannel && option.channel)
            .map((option) => option.channel);
    }

    get selectedPartners() {
        return this.internalState.selectedOptions
            .filter((option) => option.isPartner && option.partner)
            .map((option) => option.partner);
    }

    get emptyStateText() {
        return _t("No channels or people found.");
    }

    get searchPlaceholder() {
        return _t("Search channels or people");
    }

    get forwardButtonText() {
        return _t("Send");
    }

    get sourceMessageAttachments() {
        if (!this.props.sourceMessage || !this.props.sourceMessage.attachment_ids) {
            return [];
        }
        return this.props.sourceMessage.attachment_ids
            .map((id) => this.store["ir.attachment"].get(id))
            .filter(Boolean);
    }

    get sourceMessageDisplayBody() {
        if (!this.props.sourceMessage) {
            return "";
        }
        const message = this.props.sourceMessage;
        if (message.inlineBody) {
            return message.inlineBody;
        }
        if (message.bodyPreview) {
            return message.bodyPreview;
        }
        if (message.hasTextContent && message.richBody) {
            return message.richBody;
        }
        return "";
    }

    _buildOptions(channels = [], partners = []) {
        return [
            ...channels.map((channel) => ({
                id: channel.id,
                isChannel: true,
                channel,
                displayName: channel.displayName ?? "",
                avatarUrl: channel.avatarUrl ?? "",
            })),
            ...partners.map((partner) => ({
                id: partner.id,
                isPartner: true,
                partner,
                displayName: partner.displayName ?? partner.name ?? "",
                avatarUrl: partner.avatarUrl ?? "",
            })),
        ];
    }

    getOptionDisplayName(option) {
        if (option.isChannel && option.channel) {
            return option.channel.displayName ?? "";
        }
        if (option.isPartner && option.partner) {
            return option.partner.displayName ?? option.partner.name ?? "";
        }
        return super.getOptionDisplayName(option);
    }

    getOptionAvatarUrl(option) {
        if (option.isChannel && option.channel) {
            return option.channel.avatarUrl ?? "";
        }
        if (option.isPartner && option.partner) {
            return option.partner.avatarUrl ?? "";
        }
        return super.getOptionAvatarUrl(option);
    }

    _shouldExcludeThreadForForward(thread) {
        return false;
    }

    async fetchThreadsForForward() {
        this.internalState.isLoading = true;
        try {
            await this.store.channels.fetch();
            await this.sequential(async () => {
                const data = await rpc("/discuss/search", { term: this.search });
                this.store.insert(data);
            });
            const cleanedTerm = cleanTerm(this.search);
            const allChannels = Object.values(this.store["discuss.channel"].records).filter(
                (channel) =>
                    channel.channel_type &&
                    (!cleanedTerm || cleanTerm(channel.displayName).includes(cleanedTerm))
            );
            const threads = allChannels
                .map((channel) => this.store["mail.thread"].get(channel))
                .filter(Boolean)
                .sort((t1, t2) => {
                    if (t1.self_member_id && !t2.self_member_id) {
                        return -1;
                    } else if (!t1.self_member_id && t2.self_member_id) {
                        return 1;
                    }
                    return (
                        compareDatetime(t2.channel?.lastInterestDt, t1.channel?.lastInterestDt) ||
                        t2.id - t1.id
                    );
                });
            const filteredThreads = threads.filter(
                (thread) => !this._shouldExcludeThreadForForward(thread)
            );
            const allPartners = Object.values(this.store["res.partner"].records).filter(
                (partner) =>
                    partner.id !== this.store.self_user?.partner_id?.id &&
                    partner.main_user_id &&
                    (!cleanedTerm ||
                        cleanTerm(partner.displayName ?? partner.name ?? "").includes(cleanedTerm))
            );
            const partnerIdsWithChats = new Set(
                filteredThreads
                    .filter((thread) => thread.channel?.channel_type === "chat")
                    .map((thread) => thread.channel?.correspondent?.partner_id?.id)
                    .filter(Boolean)
            );
            const selectablePartners = allPartners.filter(
                (partner) => !partnerIdsWithChats.has(partner.id)
            );
            this.state.selectableChannels = filteredThreads;
            this.state.selectablePartners = selectablePartners;
        } finally {
            this.internalState.isLoading = false;
        }
    }

    onInput() {
        const value = this.inputRef.el.value;
        this.search = value;
        this.debouncedFetchThreadsForForward();
    }

    clearSearch() {
        this.search = "";
        this.debouncedFetchThreadsForForward();
    }

    _hasLinkInOptionalMsgBody(body) {
        const div = createElementWithContent("div", body);
        return Boolean(div.querySelector("a:not([data-oe-model])"));
    }

    async onClickForward() {
        if (
            !this.props.sourceMessage ||
            (this.selectedChannels.length === 0 && this.selectedPartners.length === 0)
        ) {
            return;
        }
        const targetChannelsIds = this.selectedChannels.map((channel) => channel.id);
        for (const partner of this.selectedPartners) {
            const chat = await this.store.getChat({ partnerId: partner.id });
            if (chat) {
                targetChannelsIds.push(chat.id);
            }
        }

        if (targetChannelsIds.length === 0) {
            return;
        }

        const optionalMsgBody = await prettifyMessageContent(this.state.optionalMsgBody);
        await rpc("/mail/message/forward", {
            forwarded_from_id: this.props.sourceMessage.id,
            target_channels_ids: targetChannelsIds,
            optional_msg_body: optionalMsgBody,
            optional_msg_has_link: this._hasLinkInOptionalMsgBody(optionalMsgBody),
            source_msg_has_link: this.props.sourceMessage.hasLink ?? false,
        });
        this.internalState.selectedOptions = [];
        this.state.optionalMsgBody = "";
        this.props.close?.();
        if (targetChannelsIds.length > 1) {
            this.env.services.notification.add(_t("Message forwarded successfully."), {
                type: "success",
            });
            return;
        } else if (
            targetChannelsIds[0] &&
            this.props.sourceMessage.thread?.id !== targetChannelsIds[0]
        ) {
            const thread = await this.store["mail.thread"].getOrFetch({
                model: "discuss.channel",
                id: targetChannelsIds[0],
            });
            if (thread) {
                thread.open({ focus: true });
            } else {
                this.env.services.notification.add(_t("This thread is no longer available."), {
                    type: "danger",
                });
            }
            return;
        }
    }

    getImageUrl(attachment) {
        if (attachment.uploading && attachment.tmpUrl) {
            return attachment.tmpUrl;
        }
        return url(attachment.urlRoute, {
            ...attachment.urlQueryParams,
        });
    }
}
