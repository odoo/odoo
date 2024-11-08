import { Component, useState } from "@odoo/owl";
import { useChannelActions } from "@mail/discuss/core/common/channel_actions";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useHover } from "@mail/utils/common/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {object} [activeAction]
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarChannelCommands extends Component {
    static template = "mail.DiscussSidebarChannelCommands";
    static components = { Dropdown, DropdownItem, ConfirmationDialog };
    static props = ["thread", "activeAction?", "close?"];

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.sidebarChannelActions = useChannelActions();
        this.store = useState(useService("mail.store"));
        this.notification = useDropdownState();
        this.addUser = useDropdownState();
        // Hoverable sidebar actions' configurations
        this.hoverActionConfigs = [
            {
                elementRefs: ["root_notification", "floating_notification*"],
                dropdownState: this.notification,
                actionId: "notification-settings",
            },
            {
                elementRefs: ["root_adduser", "floating_adduser*"],
                dropdownState: this.addUser,
                actionId: "add-users",
            },
        ];
        // Utility function for creating hover handler
        this.createHoverHandler = ({ elementRefs, dropdownState, actionId }) => {
            return useHover(elementRefs, {
                onHover: () => {
                    dropdownState.isOpen = true;
                    const currentAction = this.sidebarChannelActions.actions.find(
                        (action) => action.id === actionId
                    );
                    this.sidebarChannelActions.activeAction = currentAction || null;
                    this.props.activeAction(currentAction || null);
                },
                onAway: () => {
                    dropdownState.isOpen = false;
                    this.sidebarChannelActions.activeAction = null;
                    this.props.activeAction(null);
                },
            });
        };
        this.hoverActionConfigs.forEach((config) => this.createHoverHandler(config));
    }

    get chatName() {
        return this.props.thread.channel_type === "chat"
            ? this.props.thread.name
            : this.props.thread.displayName;
    }

    askConfirmation(body) {
        return new Promise((resolve) => {
            this.dialogService.add(ConfirmationDialog, {
                body: body,
                confirmLabel: _t("Leave Conversation"),
                confirm: resolve,
                cancel: () => {},
            });
        });
    }

    /**
     * @param {import("models").Thread} thread
     */
    async leaveChannel(thread) {
        if (thread.channel_type !== "group" && thread.create_uid === thread.store.self.userId) {
            await this.askConfirmation(
                _t("You are the admistrator of this channel. Are you sure you want to leave?")
            );
        }
        if (thread.channel_type === "group") {
            await this.askConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        thread.leave();
    }

    /**
     * @param {import("models").Thread} thread
     */
    channelInfo(thread) {
        if (thread) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                views: [[false, "form"]],
                res_id: thread.id,
                target: "current",
            });
        }
    }
}
