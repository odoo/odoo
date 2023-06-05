/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/thread_actions";
import { ChannelInvitation } from "@mail/discuss/core/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/channel_member_list";
import { useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry
    .add("add-users", {
        close(component, action) {
            action.popover?.close();
        },
        component: ChannelInvitation,
        componentProps(action) {
            return { close: () => action.close() };
        },
        condition(component) {
            return (
                component.thread?.model === "discuss.channel" &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        icon: "fa fa-fw fa-user-plus",
        iconLarge: "fa fa-fw fa-lg fa-user-plus",
        name: _t("Add Users"),
        nameActive: _t("Stop Adding Users"),
        open(component, action) {
            action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
                hasSizeConstraints: true,
                thread: component.thread,
            });
        },
        sequence: 30,
        setup(action) {
            const component = useComponent();
            if (!component.props.chatWindow) {
                action.popover = usePopover(ChannelInvitation, {
                    onClose: () => action.close(),
                });
            }
        },
        toggle: true,
    })
    .add("member-list", {
        component: ChannelMemberList,
        condition(component) {
            return (
                component.thread?.hasMemberList &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        icon: "fa fa-fw fa-users",
        iconLarge: "fa fa-fw fa-lg fa-users",
        name: _t("Show Member List"),
        nameActive: _t("Hide Member List"),
        sequence: 40,
        toggle: true,
    });
