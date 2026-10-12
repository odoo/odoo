import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";
import { propSignal } from "@mail/utils/common/hooks";

import {
    Component,
    computed,
    onMounted,
    onWillUnmount,
    providePlugins,
    signal,
    t,
    useListener,
    useOnChange,
    usePlugin,
    useProps,
} from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";

import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { useService } from "@web/core/utils/hooks";

export class Discuss extends Component {
    static components = {
        DiscussContent,
        MessagingMenu,
        ResizablePanel,
    };
    static template = "mail.Discuss";

    root = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            hasSidebar: t.boolean().optional(true),
        });
        this.channel = propSignal("channel", t.instanceOf(this.store["discuss.channel"]), {
            optional: true,
        });
        this.menuState = computed(() => this.store.discuss.sidebarState);
        providePlugins([MessageHighlightPlugin], { thread: () => this.thread });
        this.orm = useService("orm");
        this.effect = usePlugin(EffectPlugin);
        this.ui = useService("ui");
        useAncestors({ inDiscussApp: true });
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
            useOnChange(
                () => [this.thread, this.ui.isSmall],
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
                }
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
        return this.channel?.()?.thread || this.store.discuss.thread;
    }
}
