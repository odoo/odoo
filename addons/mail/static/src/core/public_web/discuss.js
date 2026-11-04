import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { Composer } from "@mail/core/common/composer";
import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { Thread } from "@mail/core/common/thread";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { DiscussSidebar } from "@mail/core/public_web/discuss_sidebar";
import {
    useMessageEdition,
    useMessageHighlight,
    useMessageToReplyTo,
} from "@mail/utils/common/hooks";

import {
    Component,
    onMounted,
    onWillUnmount,
    useRef,
    useState,
    useExternalListener,
    useEffect,
    useSubEnv,
} from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

export class Discuss extends Component {
    static components = {
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
    };
    static defaultProps = { hasSidebar: true };
    static template = "mail.Discuss";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.messageHighlight = useMessageHighlight();
        this.messageEdition = useMessageEdition();
        this.messageToReplyTo = useMessageToReplyTo();
        this.contentRef = useRef("content");
        this.root = useRef("root");
        this.state = useState({ jumpThreadPresent: 0 });
        this.orm = useService("orm");
        this.effect = useService("effect");
        this.ui = useState(useService("ui"));
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
                        this.chatWindow = this.thread.openChatWindow();
                    } else {
                        this.chatWindow?.close();
                    }
                },
                () => [this.thread, this.ui.isSmall]
            );
        }
        onMounted(() => (this.store.discuss.isActive = true));
        onWillUnmount(() => (this.store.discuss.isActive = false));
        useEffect(
            (memberListAction) => {
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
            },
            () => [this.threadActions.actions.find((a) => a.id === "member-list")]
        );
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
