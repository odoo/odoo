/* @odoo-module */

import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";
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
    onWillStart,
    onMounted,
    onWillUnmount,
    useChildSubEnv,
    useRef,
    useState,
    useEffect,
} from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
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
        this.messaging = useMessaging();
        this.store = useStore();
        this.threadService = useState(useService("mail.thread"));
        this.messageService = useState(useService("mail.message"));
        this.personaService = useService("mail.persona");
        this.messageHighlight = useMessageHighlight();
        this.messageEdition = useMessageEdition();
        this.messageToReplyTo = useMessageToReplyTo();
        this.contentRef = useRef("content");
        this.root = useRef("root");
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
        onWillStart(() => this.messaging.isReady);
        onMounted(() => (this.store.discuss.isActive = true));
        onWillUnmount(() => (this.store.discuss.isActive = false));
    }

    get thread() {
        return this.store.threads[this.store.discuss.threadLocalId];
    }

    get channelAvatar() {
        return this.store.inPublicPage
            ? url(
                  `/discuss/channel/${this.thread.id}/avatar_128?unique=${this.thread?.avatarCacheKey}`
              )
            : this.thread.imgUrl;
    }

    async onFileUploaded(file) {
        await this.threadService.notifyThreadAvatarToServer(this.thread.id, file.data);
        this.notification.add(_t("The avatar has been updated!"), { type: "success" });
    }

    async renameThread({ value: name }) {
        const newName = name.trim();
        if (
            newName !== this.thread.displayName &&
            ((newName && this.thread.type === "channel") ||
                this.thread.type === "chat" ||
                this.thread.type === "group")
        ) {
            await this.threadService.notifyThreadNameToServer(this.thread, newName);
        }
    }

    async updateThreadDescription({ value: description }) {
        const newDescription = description.trim();
        if (!newDescription && !this.thread.description) {
            return;
        }
        if (newDescription !== this.thread.description) {
            await this.threadService.notifyThreadDescriptionToServer(this.thread, newDescription);
        }
    }

    async renameGuest({ value: name }) {
        const newName = name.trim();
        if (this.store.guest?.name !== newName) {
            await this.personaService.updateGuestName(this.store.self, newName);
        }
    }
}
