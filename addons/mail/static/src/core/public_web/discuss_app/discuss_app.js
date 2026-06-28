import { useLayoutEffect, useRef, useSubEnv } from "@web/owl2/utils";
import { DiscussSidebar } from "@mail/core/public_web/discuss_app/sidebar/sidebar";
import { useMessageScrolling } from "@mail/utils/common/hooks";

import { Component, props, t, useListener, onMounted, onWillUnmount } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { useService } from "@web/core/utils/hooks";
import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

export class Discuss extends Component {
    static components = {
        DiscussContent,
        DiscussSidebar,
        MessagingMenu,
    };
    static template = "mail.Discuss";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            hasSidebar: t.boolean().optional(true),
            thread: t.instanceOf(this.store["mail.thread"].Class).optional(),
        });
        this.messageHighlight = useMessageScrolling({ thread: () => this.thread });
        this.root = useRef("root");
        this.orm = useService("orm");
        this.effect = useService("effect");
        this.ui = useService("ui");
        useSubEnv({
            inDiscussApp: true,
            messageHighlight: this.messageHighlight,
        });
        useListener(
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
            useLayoutEffect(
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
        onMounted(() => {
            document.body.classList.add("o_mail_discuss");
        });

        onWillUnmount(() => {
            document.body.classList.remove("o_mail_discuss");
        });
    }

    get thread() {
        return this.props.thread || this.store.discuss.thread;
    }
}
