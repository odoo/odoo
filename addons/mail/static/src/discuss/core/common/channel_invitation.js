import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import {
    PartnerSelection,
    usePartnerSelectionState,
} from "@mail/discuss/core/common/partner_selection";

import { Component, onWillStart } from "@odoo/owl";

import { useSequential } from "@mail/utils/common/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { useState } from "@web/owl2/utils";

/** @typedef {usePartnerSelectionState} usePartnerSelectionState2 */

/** Internal function for typedef */
function _useSentEmailsState() {
    return {
        /** @type {Set<string>} */
        value: new Set(),
    };
}

/** @return {ReturnType<typeof _useSentEmailsState>} */
function useSentEmailsState() {
    return useState(_useSentEmailsState());
}

export class ChannelInvitation extends Component {
    static components = { ActionPanel, PartnerSelection };
    static defaultProps = { hasSizeConstraints: false };
    static props = [
        "autofocus?",
        "hasSizeConstraints?",
        "channel?",
        "close?",
        "className?",
        "state?",
    ];
    static template = "discuss.ChannelInvitation";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.notification = useService("notification");
        this.suggestionService = useService("mail.suggestion");
        this.sequential = useSequential();
        this.internalState = usePartnerSelectionState();
        this.sentEmails = useSentEmailsState();
        this.debouncedFetchPartnersToInvite = useDebounced(
            this.fetchPartnersToInvite.bind(this),
            250
        );
        onWillStart(() => {
            if (this.store.self_user) {
                this.fetchPartnersToInvite();
            }
        });
    }

    /** @return {ReturnType<typeof usePartnerSelectionState2>} */
    get state() {
        return this.props.state || this.internalState;
    }

    get searchEmptyText() {
        return this.props.channel ? _t("No one found to invite.") : undefined;
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
                this.state.searchStr,
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
            this.state.searchStr,
            this.props.channel?.thread
        );
        this.state.searchResultCount = results["count"];
        const selectableEmails = this.state.selectedEmails.filter((addr) =>
            addr.includes(this.state.searchStr)
        );
        if (results.selectable_email) {
            selectableEmails.push(results.selectable_email);
        }
        if (results.email_already_sent) {
            this.sentEmails.value.add(results.selectable_email);
        }
        this.state.selectableEmails = [...new Set(selectableEmails)];
    }

    onInput() {
        this.debouncedFetchPartnersToInvite();
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

    onClickSelectedPartner(partner) {
        const index = this.state.selectedPartners.indexOf(partner);
        this.state.selectedPartners.splice(index, 1);
    }

    onClickSelectedEmail(email) {
        const index = this.state.selectedEmails.indexOf(email);
        this.state.selectedEmails.splice(index, 1);
    }

    onFocusInvitationLinkInput(ev) {
        ev.target.select();
    }

    async onClickInvite() {
        let channelId = this.props.channel.id;
        const invitePromises = [];
        if (this.props.channel?.channel_type === "chat") {
            const partnerIds = this.state.selectedPartners.map((partner) => partner.id);
            if (this.props.channel.correspondent?.partner_id) {
                partnerIds.unshift(this.props.channel.correspondent.partner_id.id);
            }
            if (this.state.selectedEmails.length) {
                const group = await this.store.createGroupChat({ partners_to: partnerIds });
                channelId = group.id;
            } else {
                await this.store.startChat(partnerIds);
            }
        } else if (this.state.selectedPartners.length) {
            invitePromises.push(
                this.orm.call("discuss.channel", "add_members", [[channelId]], {
                    partner_ids: this.state.selectedPartners.map((partner) => partner.id),
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
                if (this.state.selectedPartners.length === 0) {
                    return _t("Invite");
                }
                if (this.state.selectedPartners.length === 1) {
                    const alreadyChat = Object.values(this.store["discuss.channel"].records).some(
                        (channel) =>
                            channel.channel_type === "chat" &&
                            channel.correspondent?.partner_id?.eq(this.state.selectedPartners[0])
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
