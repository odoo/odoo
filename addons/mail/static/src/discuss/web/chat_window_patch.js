/* @odoo-module */

import { CallSettings } from "@mail/discuss/call_settings";
import { ChannelInvitation } from "@mail/discuss/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/channel_member_list";
import { ChatWindow } from "@mail/web/chat_window/chat_window";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ChatWindow, "discuss", {
    components: { ...ChatWindow.components, CallSettings, ChannelInvitation, ChannelMemberList },
});

patch(ChatWindow.prototype, "discuss", {
    toggleAddUsers() {
        this.state.activeMode = this.state.activeMode === "add-users" ? "" : "add-users";
    },
    toggleMemberList() {
        this.state.activeMode = this.state.activeMode === "member-list" ? "" : "member-list";
    },
    toggleSettings() {
        this.state.activeMode = this.state.activeMode === "in-settings" ? "" : "in-settings";
    },
    get actions() {
        const acts = this._super();
        if (this.props.chatWindow.isOpen && this.thread?.type === "channel") {
            acts.push({
                id: "invite",
                name:
                    this.state.activeMode === "add-users"
                        ? _t("Stop Adding Users")
                        : _t("Add Users"),
                icon: "fa fa-fw fa-user-plus",
                onSelect: () => this.toggleAddUsers(),
                sequence: 30,
            });
        }
        if (this.thread?.hasMemberList && this.props.chatWindow.isOpen) {
            acts.push({
                id: "member",
                name:
                    this.state.activeMode === "member-list"
                        ? _t("Hide Member List")
                        : _t("Show Member List"),
                icon: "fa fa-fw fa-users",
                onSelect: () => this.toggleMemberList(),
                sequence: 40,
            });
        }
        if (this.thread?.allowCalls && this.props.chatWindow.isOpen) {
            acts.push({
                id: "settings",
                name:
                    this.state.activeMode === "in-settings"
                        ? _t("Hide Call Settings")
                        : _t("Show Call Settings"),
                icon: "fa fa-fw fa-gear",
                onSelect: () => this.toggleSettings(),
                sequence: this.thread === this.rtc.state.channel ? 6 : 60,
            });
        }
        return acts;
    },
});
