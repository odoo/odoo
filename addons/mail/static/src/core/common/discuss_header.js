import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { ImStatus } from "@mail/core/common/im_status";
import { CountryFlag } from "@mail/core/common/country_flag";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Component, useRef, useState } from "@odoo/owl";
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
        CountryFlag,
    };
    static props = ["threadActions", "activeAction?"];
    static template = "mail.DiscussHeader";

    setup() {
        this.root = useRef("header");
        this.ui = useState(useService("ui"));
        this.store = useState(useService("mail.store"));
        this.notification = useService("notification");
    }

    get thread() {
        return this.store.discuss.thread;
    }

    get checkDisabledCondition() {
        return this.thread.id === "inbox" || this.thread.id === "starred"
            ? this.thread.isEmpty
            : false;
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
