import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillStart, useState } from "@odoo/owl";

import { useSequential } from "@mail/utils/common/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class ChannelInvitation extends Component {
    static components = { ActionPanel, DiscussAvatar };
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
        this.state = useState({
            searchResultCount: 0,
            searchStr: "",
            selectableEmails: [],
            selectableUsers: [],
            selectedEmails: [],
            selectedUsers: [],
            sentEmails: new Set(),
        });
        this.debouncedFetchPartnersToInvite = useDebounced(
            this.fetchPartnersToInvite.bind(this),
            250
        );
        this.inputRef = useAutofocus({ refName: "input" });
        onWillStart(() => {
            if (this.store.self_user) {
                this.fetchPartnersToInvite();
            }
        });
    }

    get selectableUsers() {
        return this.props.state?.selectableUsers ?? this.state.selectableUsers;
    }

    set selectableUsers(users) {
        if (this.props.state?.selectableUsers) {
            this.props.state.selectableUsers = users;
        } else {
            this.state.selectableUsers = users;
        }
    }

    get selectedUsers() {
        return this.props.state?.selectedUsers ?? this.state.selectedUsers;
    }

    set selectedUsers(users) {
        if (this.props.state?.selectedUsers) {
            this.props.state.selectedUsers = users;
        } else {
            this.state.selectedUsers = users;
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
            "Showing %(result_count)s results out of %(total_count)s. Narrow your search to see more choices.",
            {
                result_count: this.selectableUsers.length,
                total_count: this.state.searchResultCount,
            }
        );
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
        const selectableUsers = results.user_ids.map((id) => this.store["res.users"].get(id));
        this.selectableUsers = this.suggestionService.sortUserSuggestions(
            selectableUsers,
            this.searchStr,
            this.props.channel?.thread
        );
        this.state.searchResultCount = results["count"];
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

    onInput() {
        this.searchStr = this.inputRef.el.value;
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

    onClickSelectableUser(user) {
        if (user.in(this.selectedUsers)) {
            const index = this.selectedUsers.indexOf(user);
            if (index !== -1) {
                this.selectedUsers.splice(index, 1);
            }
            return;
        }
        this.selectedUsers.push(user);
    }

    onClickSelectableEmail(email) {
        const index = this.state.selectedEmails.indexOf(email);
        if (index !== -1) {
            this.state.selectedEmails.splice(index, 1);
            return;
        }
        this.state.selectedEmails.push(email);
    }

    onClickSelectedPartner(user) {
        const index = this.selectedUsers.indexOf(user);
        this.selectedUsers.splice(index, 1);
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
            const user_ids = this.selectedUsers.map((user) => user.id);
            if (this.props.channel.correspondent?.partner_id) {
                user_ids.unshift(this.props.channel.correspondent.partner_id.id);
            }
            if (this.state.selectedEmails.length) {
                const group = await this.store.createGroupChat({ user_ids });
                channelId = group.id;
            } else {
                await this.store.startChat(user_ids);
            }
        } else if (this.selectedUsers.length) {
            invitePromises.push(
                this.orm.call("discuss.channel", "add_members", [[channelId]], {
                    user_ids: this.selectedUsers.map((user) => user.id),
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
        this.state.selectedUsers = [];
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
                if (this.selectedUsers.length === 0) {
                    return _t("Invite");
                }
                if (this.selectedUsers.length === 1) {
                    const alreadyChat = this.selectedUsers[0].searchChat();
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
