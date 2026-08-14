import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelActionDialog } from "@mail/discuss/core/common/channel_action_dialog";

import { Component, onWillStart, proxy, signal, t, useProps, computed } from "@odoo/owl";

import { useSequential } from "@mail/utils/common/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { parseClipboard } from "./channel_invitation_clipboard";

/**
 * Open the channel invitation UI as a centered dialog, reusing {@link ChannelInvitation}.
 *
 * @param {import("@web/env").OdooEnv} env environment providing the dialog service.
 * @param {import("models").DiscussChannel} [channel] channel to invite people to.
 * @returns {void}
 */
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
    static components = { ActionPanel, DiscussAvatar };
    static template = "discuss.ChannelInvitation";

    inputRef = signal.ref();

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]).optional(),
            className: t.string().optional(),
            close: t.function([]).optional(),
            state: t
                .object({
                    searchStr: t.string().optional(),
                    selectablePartners: t.array(t.instanceOf(this.store["res.partner"])).optional(),
                    selectedPartners: t.array(t.instanceOf(this.store["res.partner"])).optional(),
                })
                .optional(),
        });
        this.rtc = useService("discuss.rtc");
        this.notification = useService("notification");
        this.suggestionService = useService("mail.suggestion");
        this.sequential = useSequential();
        this.state = proxy({
            hasPendingRequest: false,
            searchResultCount: 0,
            searchStr: "",
            selectableEmails: [],
            selectablePartners: [],
            selectedEmails: [],
            selectedPartners: [],
            sentEmails: new Set(),
            showingPartialResults: false,
        });
        this.splitSearchStr = computed(() =>
            this.searchStr
                .split(",")
                .map((term) => term.trim())
                .filter(Boolean)
        );
        this.debouncedFetchPartnersToInvite = useDebounced(
            this.fetchPartnersToInvite.bind(this),
            250
        );
        useAutofocus({ ref: this.inputRef });
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

    get showingResultNarrowText() {
        return _t(
            "Showing the first %(search_limit)s results. Narrow your search to see more choices.",
            { search_limit: this.searchLimit }
        );
    }

    get searchPlaceholder() {
        if (this.props.channel?.allow_invite_by_email) {
            return _t("Enter name or email");
        }
        return _t("Search people to invite");
    }

    get tooltipInfo() {
        let inviteOptions;
        if (this.props.channel?.allow_invite_by_email) {
            inviteOptions = [
                _t("Search for an existing user by name or email"),
                _t("Enter an email address to invite by email"),
                _t(
                    "Paste or type several email addresses, separated by commas or from your favorite spreadsheet, to select them at once"
                ),
            ];
        } else {
            inviteOptions = [
                _t("Search for an existing user by name or email"),
                _t(
                    "Paste or type several email addresses, separated by commas or from your favorite spreadsheet, to select the matching users at once"
                ),
            ];
        }
        return JSON.stringify({
            content: _t("To search for people to invite, you can:"),
            inviteOptions,
        });
    }

    async fetchPartnersToInvite() {
        const results = await this.sequential(async () => {
            this.state.hasPendingRequest = true;
            const res = await this.orm.call("res.partner", "search_for_channel_invite", [], {
                search_term: this.searchStr,
                channel_id: this.props.channel?.id ?? false,
                limit: this.searchLimit,
                with_portal_users:
                    this.props.channel &&
                    (this.props.channel.channel_type === "group" ||
                        !this.props.channel.group_public_id),
            });
            this.state.hasPendingRequest = false;
            return res;
        });
        if (!results) {
            return;
        }
        this.store.insert(results.store_data);
        for (const email of results.emails_already_sent) {
            this.state.sentEmails.add(email);
        }
        const partners = results.partner_ids.map((id) => this.store["res.partner"].get(id));
        // Several terms are a pasted list, where each entry designates one person: what it
        // resolves to is selected outright rather than offered as a suggestion to click.
        if (this.splitSearchStr().length > 1) {
            for (const partner of partners) {
                if (!partner.in(this.selectedPartners)) {
                    this.selectedPartners.push(partner);
                }
            }
            for (const email of results.selectable_emails) {
                if (!this.state.selectedEmails.includes(email)) {
                    this.state.selectedEmails.push(email);
                }
            }
            this.selectablePartners = [];
            this.state.selectableEmails = [];
            this.state.showingPartialResults = false;
            return;
        }
        this.selectablePartners = this.suggestionService.sortPartnerSuggestions(
            partners,
            this.searchStr,
            this.props.channel?.thread
        );
        this.state.showingPartialResults = results.partner_ids.length > this.searchLimit;
        const selectableEmails = this.state.selectedEmails.filter((addr) =>
            this.searchStr.split(",").some((term) => addr.includes(term.trim()))
        );
        selectableEmails.push(...results.selectable_emails);
        this.state.selectableEmails = [...new Set(selectableEmails)];
    }

    onInput() {
        this.searchStr = this.inputRef()?.value;
        this.debouncedFetchPartnersToInvite();
    }

    addPasteInputToSelection(pastedText) {
        const startPosition = this.inputRef().selectionStart;
        const endPosition = this.inputRef().selectionEnd;
        const startText = this.searchStr.slice(0, startPosition);
        const endText = this.searchStr.slice(endPosition);
        let composedSearch = "";
        if (startText.length > 0) {
            composedSearch += startText;
            if (startText.slice(-1) !== ",") {
                composedSearch += ",";
            }
        }
        composedSearch += pastedText;
        if (endText.length > 0) {
            if (endText.slice(0, 1) !== ",") {
                composedSearch += ",";
            }
            composedSearch += endText;
        }
        this.searchStr = composedSearch;
        this.debouncedFetchPartnersToInvite();
    }

    onInputPaste(ev) {
        const newSearch = parseClipboard(ev.clipboardData);
        if (newSearch) {
            ev.preventDefault();
            this.addPasteInputToSelection(newSearch);
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

    onClickSelectablePartner(partner) {
        if (partner.in(this.selectedPartners)) {
            const index = this.selectedPartners.indexOf(partner);
            if (index !== -1) {
                this.selectedPartners.splice(index, 1);
            }
            return;
        }
        this.selectedPartners.push(partner);
    }

    onClickSelectableEmail(email) {
        const index = this.state.selectedEmails.indexOf(email);
        if (index !== -1) {
            this.state.selectedEmails.splice(index, 1);
            return;
        }
        this.state.selectedEmails.push(email);
    }

    onClickSelectedPartner(partner) {
        const index = this.selectedPartners.indexOf(partner);
        this.selectedPartners.splice(index, 1);
    }

    onClickSelectedEmail(email) {
        const index = this.state.selectedEmails.indexOf(email);
        this.state.selectedEmails.splice(index, 1);
    }

    onFocusInvitationLinkInput(ev) {
        ev.target.select();
    }

    async onClickInvite() {
        const selectedPartners = this.selectedPartners;
        const selectedEmails = this.state.selectedEmails;
        if (!this.props.channel) {
            const partnerIds = selectedPartners.map((partner) => partner.id);
            await this.store.startChat(partnerIds);
            this.props.close?.();
            return;
        }
        let channelId = this.props.channel.id;
        if (this.props.channel?.channel_type === "chat") {
            const partnerIds = selectedPartners.map((partner) => partner.id);
            if (this.props.channel.correspondent?.partner_id) {
                partnerIds.unshift(this.props.channel.correspondent.partner_id.id);
            }
            if (selectedEmails.length) {
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
        } else if (selectedPartners.length || selectedEmails.length) {
            await this.store.fetchStoreData("/discuss/channel/add_members", {
                channel_id: channelId,
                partner_ids: selectedPartners.map((partner) => partner.id),
                emails: selectedEmails,
                invite_to_rtc_call: this.rtc.localChannel?.eq(this.props.channel),
            });
        }
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
                const selectedPartners = this.selectedPartners;
                if (selectedPartners.length === 0) {
                    return _t("Invite");
                }
                if (selectedPartners.length === 1) {
                    const alreadyChat = this.store["discuss.channel"].records
                        .values()
                        .some(
                            (channel) =>
                                channel.channel_type === "chat" &&
                                channel.correspondent?.partner_id?.eq(selectedPartners[0])
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
