import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { useThreadActions } from "@mail/core/common/thread_actions";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { CountryFlag } from "@mail/core/common/country_flag";
import { ActionList } from "@mail/core/common/action_list";
import { Thread } from "@mail/core/common/thread";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";

import { _t } from "@web/core/l10n/translation";
import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";

export class DiscussContent extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        CountryFlag,
        Thread,
        ThreadIcon,
        Composer,
        FileUploader,
        ImStatus,
    };
    static props = ["thread?"];
    static template = "mail.DiscussContent";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.notification = useService("notification");
        this.threadActions = useThreadActions();
        this.root = useRef("root");
        this.state = useState({ jumpThreadPresent: 0 });
        useEffect(
            () => this.actionPanelAutoOpenFn(),
            () => [this.thread]
        );
    }

    actionPanelAutoOpenFn() {
        const memberListAction = this.threadActions.actions.find((a) => a.id === "member-list");
        if (!memberListAction) {
            return;
        }
        if (this.store.discuss.isMemberPanelOpenByDefault) {
            if (!this.threadActions.activeAction) {
                memberListAction.open();
            } else if (this.threadActions.activeAction === memberListAction) {
                return; // no-op (already open)
            } else {
                this.store.discuss.isMemberPanelOpenByDefault = false;
            }
        }
    }

    get thread() {
        return this.props.thread || this.store.discuss.thread;
    }

    async onFileUploaded(file) {
        await this.thread.notifyAvatarToServer(file.data);
        this.notification.add(_t("The avatar has been updated!"), { type: "success" });
    }

    async renameGuest(name) {
        const newName = name.trim();
        if (this.store.self.name !== newName) {
            await this.store.self.updateGuestName(newName);
        }
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
}
