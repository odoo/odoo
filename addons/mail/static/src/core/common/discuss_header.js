import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussHeader extends Component {
    static components = {
        AutoresizeInput,
        ThreadIcon,
        FileUploader,
        ImStatus,
    };
    static props = ["threadActions"];
    static template = "mail.DiscussHeader";

    setup() {
        this.root = useRef("header");
        this.threadActions = this.props.threadActions;
        this.ui = useState(useService("ui"));
        this.store = useState(useService("mail.store"));
        this.notification = useService("notification");
        useEffect(
            () => {
                this.render();
            },
            () => [this.threadActions.activeAction]
        );
    }

    get checkDisabledCondition() {
        return this.store.discuss.thread.id === "inbox" ||
            this.store.discuss.thread.id === "starred"
            ? this.store.discuss.thread.isEmpty
            : false;
    }

    get thread() {
        return this.store.discuss.thread;
    }

    async onFileUploaded(file) {
        await this.thread.notifyAvatarToServer(file.data);
        this.notification.add(_t("The avatar has been updated!"), { type: "success" });
    }

    async renameThread(name) {
        await this.thread.rename(name);
    }

    async updateThreadDescription(description) {
        const newDescription = description.trim();
        if (!newDescription && !this.thread.description) {
            return;
        }
        if (newDescription !== this.thread.description) {
            await this.thread.notifyDescriptionToServer(newDescription);
        }
    }

    async renameGuest(name) {
        const newName = name.trim();
        if (this.store.self.name !== newName) {
            await this.store.self.updateGuestName(newName);
        }
    }
}
