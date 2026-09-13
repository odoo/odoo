// @ts-check
/** @odoo-module native */
import { ActionList } from "@mail/core/common/action_list";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { Thread } from "@mail/core/common/thread";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { FileUploader } from "@web/core/file_upload";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
const log = makeLogger("mail.discuss");

export class DiscussContent extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        Thread,
        ThreadIcon,
        Composer,
        FileUploader,
        ImStatus,
    };
    static props = ["thread?"];
    static template = "mail.DiscussContent";

    setup() {
        useLifecycleLog(log);
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.threadActions = useThreadActions({ thread: () => this.thread });
        this.root = useRef("root");
        this.state = useState({ jumpThreadPresent: 0 });
        this.isDiscussContent = true;
        useEffect(
            () => this.actionPanelAutoOpenFn(),
            () => [this.thread],
        );
    }

    actionPanelAutoOpenFn() {
        const memberListAction = this.threadActions.actions.find(
            (a) => a.id === "member-list",
        );
        if (memberListAction && this.store.discuss.isMemberPanelOpenByDefault) {
            log.logic("member panel auto-open", () => ({
                thread: this.thread?.localId,
            }));
            memberListAction.open();
        }
    }

    get thread() {
        return this.props.thread || this.store.discuss.thread;
    }

    get showImStatus() {
        return this.thread.isDirectChat;
    }

    get showThreadAvatar() {
        return ["channel", "group", "chat"].includes(this.thread.channel_type);
    }

    get isThreadAvatarEditable() {
        return (
            !this.thread.parent_channel_id &&
            this.thread.is_editable &&
            this.thread.isMultiMemberChannel
        );
    }

    /** @param {{data: string}} file */
    async onFileUploaded(file) {
        log.logic("avatar upload", () => ({ thread: this.thread.localId }));
        await this.thread.notifyAvatarToServer(file.data);
        this.notification.add(_t("The avatar has been updated!"), { type: "success" });
    }

    /** @param {string} name */
    async renameGuest(name) {
        const newName = name.trim();
        if (this.store.self.name !== newName) {
            await this.store.self_guest?.updateGuestName(newName);
        }
    }

    /** @param {string} name */
    async renameThread(name) {
        log.logic("renameThread", () => ({ thread: this.thread.localId, name }));
        await this.thread.rename(name);
    }

    /** @param {string} description */
    async updateThreadDescription(description) {
        const newDescription = description.trim();
        if (!newDescription && !this.thread.description) {
            return;
        }
        if (newDescription !== this.thread.description) {
            log.logic("updateThreadDescription", () => ({
                thread: this.thread.localId,
            }));
            await this.thread.notifyDescriptionToServer(newDescription);
        }
    }
}
