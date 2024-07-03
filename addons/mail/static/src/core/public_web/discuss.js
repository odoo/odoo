import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { Thread } from "@mail/core/common/thread";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import {
    useMessageEdition,
    useMessageHighlight,
    useMessageToReplyTo,
} from "@mail/utils/common/hooks";

import {
    Component,
    onMounted,
    onWillUnmount,
    useChildSubEnv,
    useRef,
    useState,
    useEffect,
    useExternalListener,
} from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";

export class Discuss extends Component {
    static components = {
        AutoresizeInput,
        Thread,
        ThreadIcon,
        Composer,
        FileUploader,
        ImStatus,
    };
    static props = {};
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
        this.prevInboxCounter = this.store.discuss.inbox.counter;
        useChildSubEnv({
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
        useEffect(
            () => {
                if (
                    this.thread?.id === "inbox" &&
                    this.prevInboxCounter !== this.store.discuss.inbox.counter &&
                    this.store.discuss.inbox.counter === 0
                ) {
                    this.effect.add({
                        message: _t("Congratulations, your inbox is empty!"),
                        type: "rainbow_man",
                        fadeout: "fast",
                    });
                }
                this.prevInboxCounter = this.store.discuss.inbox.counter;
            },
            () => [this.store.discuss.inbox.counter]
        );
        onMounted(() => (this.store.discuss.isActive = true));
        onWillUnmount(() => (this.store.discuss.isActive = false));
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
