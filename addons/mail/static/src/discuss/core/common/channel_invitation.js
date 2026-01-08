import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { SelectableList } from "@mail/discuss/core/common/selectable_list";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { MessageLinkPreviewList } from "@mail/core/common/message_link_preview_list";
import { Gif } from "@mail/core/common/gif";

import { onMounted, onWillStart, useEffect, useState } from "@odoo/owl";

import { useSequential } from "@mail/utils/common/hooks";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class ChannelInvitation extends SelectableList {
    static components = {
        ...SelectableList.components,
        ActionPanel,
        DiscussAvatar,
        AttachmentList,
        MessageLinkPreviewList,
        Gif,
    };
    static defaultProps = { hasSizeConstraints: false };
    static props = [
        "autofocus?",
        "hasSizeConstraints?",
        "channel?",
        "close?",
        "className?",
        "searchStr?",
        "onSelectionChange?",
    ];
    static template = "discuss.ChannelInvitation";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.notification = useService("notification");
        this.suggestionService = useService("mail.suggestion");
        this.ui = useService("ui");
        this.sequential = useSequential();
        this.state = useState({
            searchResultCount: 0,
            searchStr: this.props.searchStr ?? "",
            selectableEmails: [],
            selectablePartners: [],
            sentEmails: new Set(),
        });
        this.internalState.search = this.state.searchStr;
        this.debouncedFetchPartnersToInvite = useDebounced(
            this.fetchPartnersToInvite.bind(this),
            250
        );
        this.inputRef = useAutofocus({ refName: "input" });
        const originalToggleSelection = this.toggleSelection;
        this.toggleSelection = (option) => {
            originalToggleSelection.call(this, option);
            if (this.props.onSelectionChange) {
                this.props.onSelectionChange(this.selectedPartners);
            }
        };
        onWillStart(() => {
            if (this.store.self_user) {
                this.fetchPartnersToInvite();
            }
        });
        onMounted(() => {
            if (this.store.self_user && this.props.channel) {
                this.inputRef.el.focus();
            }
        });
        useEffect(
            () => {
                if (this.props.autofocus) {
                    this.inputRef.el?.focus();
                }
            },
            () => [this.props.autofocus]
        );
        useEffect(
            () => {
                if (this.props.onSelectionChange) {
                    this.props.onSelectionChange(this.selectedPartners);
                }
            },
            () => []
        );
    }

    get selectedPartners() {
        return this.internalState.selectedOptions
            .filter((option) => option.isPartner && option.partner)
            .map((option) => option.partner);
    }

    get selectedEmails() {
        return this.internalState.selectedOptions
            .filter((option) => option.email)
            .map((option) => option.email);
    }

    get searchStr() {
        return this.state.searchStr;
    }

    set searchStr(newSearchStr) {
        this.state.searchStr = newSearchStr;
        this.internalState.search = newSearchStr;
    }

    get showingResultNarrowText() {
        return _t(
            "Showing %(result_count)s results out of %(total_count)s. Narrow your search to see more choices.",
            {
                result_count: this.state.selectablePartners.length,
                total_count: this.state.searchResultCount,
            }
        );
    }

    _buildOptions(partners, emails) {
        return [
            ...partners.map((partner) => ({
                id: partner.id,
                isPartner: true,
                partner,
                displayName: partner.name ?? "",
                avatarUrl: partner.avatarUrl ?? "",
            })),
            ...emails.map((email) => ({
                id: `email_${email}`,
                isPartner: false,
                email,
                displayName: email,
                avatarUrl: "",
            })),
        ];
    }

    get options() {
        return this._buildOptions(this.state.selectablePartners, this.state.selectableEmails);
    }

    getOptionDisplayName(option) {
        if (option.isPartner && option.partner) {
            return option.partner.name ?? "";
        }
        return option.email ?? super.getOptionDisplayName(option);
    }

    getOptionAvatarUrl(option) {
        return option.isPartner && option.partner
            ? option.partner.avatarUrl ?? ""
            : super.getOptionAvatarUrl(option);
    }

    get emptyStateText() {
        if (this.props.channel) {
            return _t("No people found to invite.");
        }
        return _t("No user found.");
    }

    get searchPlaceholder() {
        if (this.props.channel?.allow_invite_by_email) {
            return _t("Enter name or email");
        }
        return _t("Search people to invite");
    }

    async fetchPartnersToInvite() {
        const results = await this.sequential(() =>
            this.orm.call("res.partner", "search_for_channel_invite", [
                this.searchStr,
                this.props.channel?.id ?? false,
            ])
        );
        if (!results) {
            return;
        }
        this.store.insert(results.store_data);
        const selectablePartners = results.partner_ids.map((id) =>
            this.store["res.partner"].get(id)
        );
        this.state.selectablePartners = this.suggestionService.sortPartnerSuggestions(
            selectablePartners,
            this.searchStr,
            this.props.channel?.thread
        );
        this.state.searchResultCount = results["count"];
        const selectableEmails = this.selectedEmails.filter((addr) =>
            addr.includes(this.searchStr)
        );
        if (results.selectable_email) {
            selectableEmails.push(results.selectable_email);
        }
        if (results.email_already_sent) {
            this.state.sentEmails.add(results.selectable_email);
        }
        this.state.selectableEmails = [...new Set(selectableEmails)];
    }

    onInput() {
        const value = this.inputRef.el.value;
        this.searchStr = value;
        this.debouncedFetchPartnersToInvite();
    }

    clearSearch() {
        this.searchStr = "";
        this.debouncedFetchPartnersToInvite();
    }

    onFocusInvitationLinkInput(ev) {
        ev.target.select();
    }

    async onClickCopy(ev) {
        let notification = _t("Invitation link copied!");
        let type = "success";
        const clipboard = this.env.inDiscussCallView?.isPip
            ? this.rtc.pipService.pipWindow?.navigator.clipboard
            : navigator.clipboard;
        try {
            await clipboard.writeText(this.props.channel.invitationLink);
        } catch {
            notification = _t("Invitation link copy failed (Permission denied?)!");
            type = "danger";
        }
        this.notification.add(notification, { type });
    }

    async onClickInvite() {
        let channelId = this.props.channel.id;
        const invitePromises = [];
        if (this.props.channel?.channel_type === "chat") {
            const partnerIds = this.selectedPartners.map((partner) => partner.id);
            if (this.props.channel.correspondent?.partner_id) {
                partnerIds.unshift(this.props.channel.correspondent.partner_id.id);
            }
            if (this.state.selectedEmails.length) {
                const group = await this.store.createGroupChat({ partners_to: partnerIds });
                channelId = group.id;
            } else {
                await this.store.startChat(partnerIds);
            }
        } else if (this.selectedPartners.length) {
            invitePromises.push(
                this.orm.call("discuss.channel", "add_members", [[channelId]], {
                    partner_ids: this.selectedPartners.map((partner) => partner.id),
                    invite_to_rtc_call: this.rtc.localChannel?.eq(this.props.channel),
                })
            );
        }
        if (this.selectedEmails.length) {
            invitePromises.push(
                this.orm.call("discuss.channel", "invite_by_email", [channelId], {
                    emails: this.state.selectedEmails,
                })
            );
        }
        await Promise.all(invitePromises);
        this.internalState.selectedOptions = [];
        this.props.close?.();
    }

    get invitationButtonText() {
        if (!this.props.channel) {
            return "";
        }
        if (this.props.channel.default_display_mode === "video_full_screen") {
            return _t("Invite to Meeting");
        }
        if (this.props.channel.channel_type === "channel") {
            return _t("Invite");
        } else if (this.props.channel.channel_type === "group") {
            return _t("Invite to Group Chat");
        } else if (this.props.channel.channel_type === "chat") {
            if (this.props.channel.correspondent?.persona.eq(this.store.self)) {
                if (this.selectedPartners.length === 0) {
                    return _t("Invite");
                }
                if (this.selectedPartners.length === 1) {
                    const alreadyChat = Object.values(this.store["discuss.channel"].records).some(
                        (channel) =>
                            channel.channel_type === "chat" &&
                            channel.correspondent?.partner_id?.eq(this.selectedPartners[0])
                    );
                    if (alreadyChat) {
                        return _t("Go to conversation");
                    }
                    return _t("Start a Conversation");
                }
            }
            return _t("Create Group Chat");
        }
        return _t("Invite");
    }
}
