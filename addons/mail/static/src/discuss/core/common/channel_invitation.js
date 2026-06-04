import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelActionDialog } from "@mail/discuss/core/common/channel_action_dialog";
import { DiscussSelectableList } from "@mail/discuss/core/common/selectable_list";

import { Component, onWillStart, props, proxy, t } from "@odoo/owl";

import { useSequential } from "@mail/utils/common/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { useSubEnv } from "@web/owl2/utils";

function partnerItem(partner) {
    return {
        key: `partner-${partner.id}`,
        label: partner.name,
        subtitle: partner.email,
        avatarRecord: partner,
        partner,
    };
}

function emailItem(email, subtitle) {
    return { key: `email-${email}`, label: email, subtitle, avatarIcon: "fa fa-envelope", email };
}

export function openChannelInvitationDialog(env, channel) {
    env.services.dialog.add(ChannelActionDialog, {
        contentClass: "o-discuss-ChannelInvitation",
        contentComponent: ChannelInvitation,
        contentProps: {
            channel,
            close: () => env.services.dialog.closeAll(),
        },
        title: channel?.displayName ?? _t("New Chat"),
    });
}

export class ChannelInvitation extends Component {
    static components = { ActionPanel, DiscussSelectableList };
    static template = "discuss.ChannelInvitation";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.props = props({
            channel: t.instanceOf(this.store["discuss.channel"].Class).optional(),
            className: t.string().optional(),
            close: t.function([]).optional(),
            state: t
                .object({
                    searchStr: t.string().optional(),
                    selectablePartners: t
                        .array(t.instanceOf(this.store["res.partner"].Class))
                        .optional(),
                    selectedPartners: t
                        .array(t.instanceOf(this.store["res.partner"].Class))
                        .optional(),
                })
                .optional(),
        });
        this.rtc = useService("discuss.rtc");
        this.suggestionService = useService("mail.suggestion");
        this.sequential = useSequential();
        this.state = proxy({
            hasPendingRequest: false,
            searchStr: "",
            selectableEmails: [],
            selectablePartners: [],
            selectedEmails: [],
            selectedPartners: [],
            sentEmails: new Set(),
            showingPartialResults: false,
        });
        this.debouncedFetchPartnersToInvite = useDebounced(
            this.fetchPartnersToInvite.bind(this),
            250
        );
        useSubEnv({ invitationChannel: this.props.channel });
        onWillStart(() => {
            if (this.store.self_user) {
                this.fetchPartnersToInvite();
            }
        });
    }

    get searchLimit() {
        return 15;
    }

    get selectablePartners() {
        return this.props.state?.selectablePartners ?? this.state.selectablePartners;
    }

    set selectablePartners(partners) {
        if (this.props.state?.selectablePartners) {
            this.props.state.selectablePartners = partners;
        } else {
            this.state.selectablePartners = partners;
        }
    }

    get selectedPartners() {
        return this.props.state?.selectedPartners ?? this.state.selectedPartners;
    }

    set selectedPartners(partners) {
        if (this.props.state?.selectedPartners) {
            this.props.state.selectedPartners = partners;
        } else {
            this.state.selectedPartners = partners;
        }
    }

    get searchStr() {
        return this.props.state?.searchStr ?? this.state.searchStr;
    }

    set searchStr(newSearchStr) {
        if (this.props.state?.searchStr !== undefined) {
            this.props.state.searchStr = newSearchStr;
        } else {
            this.state.searchStr = newSearchStr;
        }
    }

    get searchPlaceholder() {
        if (this.props.channel?.allow_invite_by_email) {
            return _t("Enter name or email");
        }
        return _t("Search people to invite");
    }

    get emptyText() {
        return this.props.channel ? _t("No one found to invite.") : _t("No users found.");
    }

    get search() {
        return {
            inputId: "o-discuss-ChannelInvitation-search",
            onInput: (value) => this.onSearchInput(value),
            placeholder: this.searchPlaceholder,
            value: this.searchStr,
        };
    }

    get showingResultNarrowText() {
        return _t(
            "Showing the first %(search_limit)s results. Narrow your search to see more choices.",
            { search_limit: this.searchLimit }
        );
    }

    get selectableItems() {
        const items = this.selectablePartners.map(partnerItem);
        for (const email of this.state.selectableEmails) {
            items.push(
                emailItem(
                    email,
                    this.state.sentEmails.has(email)
                        ? _t("Invitation already sent to this address")
                        : undefined
                )
            );
        }
        return items;
    }

    get selectedItems() {
        return [
            ...this.selectedPartners.map(partnerItem),
            ...this.state.selectedEmails.map((email) => emailItem(email)),
        ];
    }

    async fetchPartnersToInvite() {
        const results = await this.sequential(async () => {
            this.state.hasPendingRequest = true;
            const res = await this.orm.call("res.partner", "search_for_channel_invite", [], {
                search_term: this.searchStr,
                channel_id: this.props.channel?.id ?? false,
                limit: this.searchLimit,
            });
            this.state.hasPendingRequest = false;
            return res;
        });
        if (!results) {
            return;
        }
        this.store.insert(results.store_data);
        const selectablePartners = results.partner_ids.map((id) =>
            this.store["res.partner"].get(id)
        );
        this.selectablePartners = this.suggestionService.sortPartnerSuggestions(
            selectablePartners,
            this.searchStr,
            this.props.channel?.thread
        );
        this.state.showingPartialResults = results.partner_ids.length > this.searchLimit;
        const selectableEmails = this.state.selectedEmails.filter((addr) =>
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

    onSearchInput(value) {
        this.searchStr = value;
        this.debouncedFetchPartnersToInvite();
    }

    onToggle(item) {
        if (item.partner) {
            if (item.partner.in(this.selectedPartners)) {
                this.selectedPartners.splice(this.selectedPartners.indexOf(item.partner), 1);
            } else {
                this.selectedPartners.push(item.partner);
            }
            return;
        }
        const index = this.state.selectedEmails.indexOf(item.email);
        if (index === -1) {
            this.state.selectedEmails.push(item.email);
        } else {
            this.state.selectedEmails.splice(index, 1);
        }
    }

    onClickGenerateNewLink() {
        this.env.services.dialog.add(ConfirmationDialog, {
            title: _t("Warning"),
            body: _t(
                "You're about to create a new invite link. The current link will no longer grant guests access to the channel. Do you want to proceed?"
            ),
            cancel: () => {},
            confirmLabel: _t("Generate"),
            confirm: () =>
                this.orm.call("discuss.channel", "action_reset_invitation_uuid", [
                    [this.props.channel.id],
                ]),
        });
    }

    onFocusInvitationLinkInput(ev) {
        ev.target.select();
    }

    async onClickInvite() {
        if (!this.props.channel) {
            const partnerIds = this.selectedPartners.map((partner) => partner.id);
            await this.store.startChat(partnerIds);
            this.props.close?.();
            return;
        }
        let channelId = this.props.channel.id;
        const invitePromises = [];
        if (this.props.channel?.channel_type === "chat") {
            const partnerIds = this.selectedPartners.map((partner) => partner.id);
            if (this.props.channel.correspondent?.partner_id) {
                partnerIds.unshift(this.props.channel.correspondent.partner_id.id);
            }
            if (this.state.selectedEmails.length) {
                const users_to = [
                    ...new Set([
                        ...partnerIds
                            .map(
                                (partnerId) =>
                                    this.store["res.partner"].get(partnerId)?.main_user_id?.id
                            )
                            .filter(Boolean),
                    ]),
                ];
                const group = await this.store.createGroupChat({ users_to });
                channelId = group.id;
            } else {
                await this.store.startChat(partnerIds);
            }
        } else if (this.selectedPartners.length) {
            invitePromises.push(
                this.store.fetchStoreData("/discuss/channel/add_members", {
                    channel_id: channelId,
                    partner_ids: this.selectedPartners.map((partner) => partner.id),
                    invite_to_rtc_call: this.rtc.localChannel?.eq(this.props.channel),
                })
            );
        }
        if (this.state.selectedEmails.length) {
            invitePromises.push(
                this.orm.call("discuss.channel", "invite_by_email", [channelId], {
                    emails: this.state.selectedEmails,
                })
            );
        }
        await Promise.all(invitePromises);
        this.state.selectedEmails = [];
        this.state.selectedPartners = [];
        this.props.close?.();
    }

    get inviteTitle() {
        const name = this.props.channel?.displayName;
        if (this.props.channel?.default_display_mode === "video_full_screen") {
            return _t('Invite people to "%(name)s"', { name });
        }
        if (this.props.channel?.channel_type === "channel") {
            return _t('Invite people to the channel "%(name)s"', { name });
        }
        return _t("Invite people");
    }

    get invitationButtonText() {
        if (!this.props.channel) {
            return _t("Create Chat");
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
