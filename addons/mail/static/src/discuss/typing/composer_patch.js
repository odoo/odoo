/* @odoo-module */

import { Composer } from "@mail/composer/composer";
import { Typing } from "@mail/discuss/typing/typing";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { useDebounced } from "@web/core/utils/timing";

const commandRegistry = registry.category("discuss.channel_commands");

export const SHORT_TYPING = 5000;
export const LONG_TYPING = 50000;

patch(Composer, "discuss/typing", {
    components: { ...Composer.components, Typing },
});

patch(Composer.prototype, "discuss/typing", {
    /**
     * @override
     */
    setup() {
        this._super();
        this.typingNotified = false;
        this.stopTypingDebounced = useDebounced(this.stopTyping.bind(this), SHORT_TYPING);
    },
    async startWysiwyg(wysiwyg) {
        await this._super(...arguments);
        this.wysiwyg.odooEditor.editable.addEventListener("input", () => {
            this.onInput();
        });
    },
    /**
     * Notify the server of the current typing status
     *
     * @param {boolean} [is_typing=true]
     */
    notifyIsTyping(is_typing = true) {
        if (["chat", "channel", "group"].includes(this.thread?.type)) {
            this.messaging.rpc(
                "/discuss/channel/notify_typing",
                {
                    channel_id: this.thread.id,
                    is_typing,
                },
                { silent: true }
            );
        }
    },
    /**
     * @param {InputEvent} ev
     */
    onInput(ev) {
        const value = this.wysiwyg.odooEditor.editable.textContent;
        if (this.thread?.model === "discuss.channel" && value.startsWith("/")) {
            const [firstWord] = value.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                value === "/" || // suggestions not yet started
                this.hasSuggestions ||
                (command &&
                    (!command.channel_types || command.channel_types.includes(this.thread.type)))
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
        await this._super();
        this.stopTyping();
    },
    stopTyping() {
        if (this.typingNotified) {
            this.typingNotified = false;
            this.notifyIsTyping(false);
        }
    },
});
