import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { Composer } from "@mail/core/common/composer";
import { CountryFlag } from "@mail/core/common/country_flag";
import { ActionList } from "@mail/core/common/action_list";
import { ImStatus } from "@mail/core/common/im_status";
import { Thread } from "@mail/core/common/thread";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { DiscussSidebar } from "@mail/core/public_web/discuss_sidebar";
import { useMessageScrolling } from "@mail/utils/common/hooks";

import { Component, useRef, useState, useExternalListener, useEffect, useSubEnv } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

export class Discuss extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        CountryFlag,
        DiscussSidebar,
        Thread,
        ThreadIcon,
        Composer,
        FileUploader,
        ImStatus,
        MessagingMenu,
    };
    static props = {
        hasSidebar: { type: Boolean, optional: true },
        thread: { optional: true },
    };
    static defaultProps = { hasSidebar: true };
    static template = "mail.Discuss";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.messageHighlight = useMessageScrolling();
        this.contentRef = useRef("content");
        this.root = useRef("root");
        this.state = useState({ jumpThreadPresent: 0 });
        this.orm = useService("orm");
        this.effect = useService("effect");
        this.ui = useService("ui");
        useSubEnv({
            inDiscussApp: true,
            messageHighlight: this.messageHighlight,
        });
        this.notification = useService("notification");
        this.threadActions = useThreadActions();
        useExternalListener(
            window,
            "keydown",
            (ev) => {
                if (getActiveHotkey(ev) === "escape" && !this.thread?.composer?.isFocused) {
                    if (this.thread?.composer) {
                        this.thread.composer.autofocus++;
                    }
                }
                if (getActiveHotkey(ev) === "control+k") {
                    this.store.env.services.command.openMainPalette({ searchValue: "@" });
                    ev.preventDefault();
                    ev.stopPropagation();
                }
            },
            { capture: true }
        );
        if (this.store.inPublicPage) {
            useEffect(
                (thread, isSmall) => {
                    if (!thread) {
                        return;
                    }
                    if (isSmall) {
                        this.thread
                            .openChatWindow({ focus: true })
                            .then((chatWindow) => (this.chatWindow = chatWindow));
                    } else {
                        this.chatWindow?.close();
                    }
                },
                () => [this.thread, this.ui.isSmall]
            );
        }
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
