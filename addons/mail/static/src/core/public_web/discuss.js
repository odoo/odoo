import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { useThreadActions } from "@mail/core/common/thread_actions";
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
    useChildSubEnv,
    useRef,
    useState,
    useExternalListener,
    useEffect,
} from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { useService } from "@web/core/utils/hooks";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { DiscussHeader } from "@mail/core/common/discuss_header";

export class Discuss extends Component {
    static components = {
        DiscussSidebar,
        Thread,
        Composer,
        MessagingMenu,
        DiscussHeader,
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
    }

    get thread() {
        return this.store.discuss.thread;
    }
}
