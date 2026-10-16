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
    useEffect,
    useListener,
    useOnChange,
    usePlugin,
    useProps,
} from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";

import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { attClassObjectToString } from "@mail/utils/common/format";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useService } from "@web/core/utils/hooks";

/**
 * Ends the toggling when no `transitionend` does. Longer than the 150ms width transition, set by
 * `--mail-Discuss-transition` in `discuss_app.css`.
 */
const SIDEBAR_TOGGLING_TIMEOUT = 500;

export class Discuss extends Component {
    static components = {
        DiscussContent,
        MessagingMenu,
        ResizablePanel,
    };
    static template = "mail.Discuss";

    /** Whether the sidebar width is animating after a toggle (not while resizing). */
    isSidebarToggling = signal(false);
    root = signal.ref();
    sidebarClass = computed(() =>
        attClassObjectToString({
            "o-mail-DiscussApp-sidebar d-flex flex-column flex-shrink-0 h-100 z-1 d-print-none": true,
            "o-collapsed": this.store.discuss.isSidebarCollapsed,
            "o-toggling": this.isSidebarToggling(),
        })
    );

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
        this.effect = usePlugin(EffectPlugin);
        this.ui = usePlugin(UIPlugin);
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
                () => [this.thread, this.ui.isSmall()],
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
        useEffect(() => {
            if (!this.isSidebarToggling()) {
                return;
            }
            const timeout = setTimeout(
                () => this.isSidebarToggling.set(false),
                SIDEBAR_TOGGLING_TIMEOUT
            );
            return () => clearTimeout(timeout);
        });
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

    /** @param {TransitionEvent} ev */
    onTransitionend(ev) {
        if (
            ev.propertyName === "width" &&
            ev.target.classList.contains("o-mail-DiscussApp-sidebar")
        ) {
            this.isSidebarToggling.set(false);
        }
    }

    toggleSidebar() {
        this.store.discuss.isSidebarCollapseEnabled = !this.store.discuss.isSidebarCollapseEnabled;
        this.isSidebarToggling.set(true);
    }
}
