import { Composer } from "@mail/core/common/composer";
import { Typing } from "@mail/discuss/typing/common/typing";
import { rpc } from "@web/core/network/rpc";

import { onWillDestroy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useDebounced } from "@web/core/utils/timing";

const commandRegistry = registry.category("discuss.channel_commands");

export const SHORT_TYPING = 5000;
export const LONG_TYPING = 50000;

patch(Composer, {
    components: { ...Composer.components, Typing },
});

patch(Composer.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.typingNotified = false;
        this.stopTypingDebounced = useDebounced(this.stopTyping.bind(this), SHORT_TYPING);
        onWillDestroy(() => {
            this.stopTyping();
        });
    },
    /**
     * Notify the server of the current typing status
     *
     * @param {boolean} [is_typing=true]
     */
    notifyIsTyping(is_typing = true) {
        if (this.thread?.model === "discuss.channel" && this.thread.id > 0) {
            rpc(
                "/discuss/channel/notify_typing",
                {
                    channel_id: this.thread.id,
                    is_typing,
                },
                { silent: true }
            );
        }
    },
    /** @override */
    onInput(ev) {
        super.onInput(ev);
        this.detectTyping(ev);
    },
    detectTyping() {
        const value = this.props.composer.composerText;
        if (this.thread?.model === "discuss.channel" && value.startsWith("/")) {
            const [firstWord] = value.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                value === "/" || // suggestions not yet started
                this.hasSuggestions ||
                (command &&
                    (!command.channel_types ||
                        command.channel_types.includes(this.thread.channel_type)))
            ) {
                this.stopTyping();
                return;
            }
        }
        if (!this.typingNotified && value) {
            this.typingNotified = true;
            this.notifyIsTyping();
            browser.setTimeout(() => (this.typingNotified = false), LONG_TYPING);
        }
        this.stopTypingDebounced();
    },
    /**
     * @override
     */
    async sendMessage() {
        await super.sendMessage();
        this.stopTyping();
    },
    stopTyping() {
        if (this.typingNotified) {
            this.typingNotified = false;
            this.notifyIsTyping(false);
        }
    },
    addEmoji(str) {
        const res = super.addEmoji(str);
        this.detectTyping();
        return res;
    },
});
