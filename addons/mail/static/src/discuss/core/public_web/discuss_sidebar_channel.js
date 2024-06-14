import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";
import { discussSidebarChannelIndicatorsRegistry } from "./discuss_sidebar_channel_indicators_registry";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarChannel extends Component {
    static template = "mail.DiscussSidebarChannel";
    static props = ["thread"];
    static components = { ImStatus, ThreadIcon };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.root = useRef("root");
        useEffect(
            () => {
                if (this.props.thread.eq(this.store.discuss.thread)) {
                    this.env.discussSidebar.setActiveRef(this.root);
                }
            },
            () => [this.store.discuss.thread]
        );
    }

    get channelIndicators() {
        return discussSidebarChannelIndicatorsRegistry.getAll();
    }

    get isUnread() {
        return (
            this.props.thread.selfMember?.message_unread_counter > 0 &&
            !this.props.thread.mute_until_dt
        );
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

    async leaveChannel() {
        if (
            this.props.thread.channel_type !== "group" &&
            this.props.thread.create_uid === this.props.thread.store.self.userId
        ) {
            await this.askConfirmation(
                _t("You are the administrator of this channel. Are you sure you want to leave?")
            );
        }
        if (this.props.thread.channel_type === "group") {
            await this.askConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        this.props.thread.leave();
    }

    /** @param {MouseEvent} ev */
    openThread(ev) {
        markEventHandled(ev, "sidebar.openThread");
        this.props.thread.setAsDiscussThread();
    }
}
