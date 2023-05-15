/* @odoo-module */

import { CallSettings } from "@mail/discuss/core/call_settings";
import { ChannelInvitation } from "@mail/discuss/core/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/channel_member_list";
import { ChatWindow } from "@mail/chat_window/chat_window";
import { Call } from "@mail/discuss/rtc/call";
import { useRtc } from "@mail/discuss/rtc/rtc_hook";
import { createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(ChatWindow, "discuss", {
    components: {
        ...ChatWindow.components,
        CallSettings,
        ChannelInvitation,
        ChannelMemberList,
        Call,
    },
});

patch(ChatWindow.prototype, "discuss", {
    setup(env, services) {
        this._super(...arguments);
        this.rtc = useRtc();
        this.discussStore = useState(useService("discuss.store"));
    },
    toggleAddUsers() {
        this.state.activeMode = this.state.activeMode === "add-users" ? "" : "add-users";
    },
    toggleMemberList() {
        this.state.activeMode = this.state.activeMode === "member-list" ? "" : "member-list";
    },
    toggleSettings() {
        this.state.activeMode = this.state.activeMode === "in-settings" ? "" : "in-settings";
    },
    getChannel() {
        return this.discussStore.channels[
            createLocalId("discuss.channel", this.props.chatWindow.thread?.id)
        ];
    },
    get actions() {
        const acts = this._super();
        const channel = this.getChannel();
        if (this.props.chatWindow.isOpen && channel) {
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
        if (channel?.hasMemberList && this.props.chatWindow.isOpen) {
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
        if (channel?.allowCalls && this.props.chatWindow.isOpen) {
            acts.push({
                id: "settings",
                name:
                    this.state.activeMode === "in-settings"
                        ? _t("Hide Call Settings")
                        : _t("Show Call Settings"),
                icon: "fa fa-fw fa-gear",
                onSelect: () => this.toggleSettings(),
                sequence: channel.localId === this.rtc.state.channel?.localId ? 6 : 60,
            });
        }
        if (
            channel?.allowCalls &&
            channel.localId !== this.rtc.state.channel?.localId &&
            !this.props.chatWindow.hidden
        ) {
            acts.push({
                id: "call",
                name: _t("Start a Call"),
                icon: "fa fa-fw fa-phone",
                onSelect: () => this.rtc.toggleCall(channel),
                sequence: 10,
            });
        }
        return acts;
    },
});
