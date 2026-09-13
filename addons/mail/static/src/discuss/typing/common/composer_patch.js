// @ts-check
/** @odoo-module native */
import { Composer } from "@mail/core/common/composer";
import { Typing } from "@mail/discuss/typing/common/typing";
import { onWillDestroy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useDebounced } from "@web/core/utils/timing";

const log = makeLogger("mail.typing");
const commandRegistry = registry.category("discuss.channel_commands");

export const SHORT_TYPING = 5000;
export const LONG_TYPING = 50000;

patch(Composer, {
    components: { ...Composer.components, Typing },
});

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.typingNotified = false;
        this.serverKnowsTyping = false;
        this.stopTypingDebounced = useDebounced(
            this.stopTyping.bind(this),
            SHORT_TYPING,
        );
        onWillDestroy(() => {
            this.stopTyping();
        });
    },
    /** @param {boolean} [is_typing=true] */
    notifyIsTyping(is_typing = true) {
        if (this.thread?.isChannelKind && !this.thread.isTransient) {
            log.logic("notifyIsTyping", () => ({
                thread: this.thread.localId,
                is_typing,
            }));
            rpc(
                "/discuss/channel/notify_typing",
                {
                    channel_id: this.thread.id,
                    is_typing,
                },
                { silent: true },
            );
        }
    },
    /** @param {InputEvent} ev */
    onInput(ev) {
        super.onInput(ev);
        this.updateTypingState();
    },
    updateTypingState() {
        if (this.props.composer.message) {
            return;
        }
        const value = this.props.composer.composerText;
        if (this.thread?.isChannelKind && value.startsWith("/")) {
            const [firstWord] = value.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                value === "/" ||
                this.hasSuggestions ||
                (command &&
                    (!command.condition ||
                        command.condition({
                            store: this.store,
                            thread: this.thread,
                        })) &&
                    (!command.channel_types ||
                        command.channel_types.includes(this.thread.channel_type)))
            ) {
                log.logic("command input does not count as typing", () => ({
                    thread: this.thread.localId,
                    firstWord,
                }));
                this.stopTyping();
                return;
            }
        }
        if (!this.typingNotified && value) {
            this.typingNotified = true;
            this.serverKnowsTyping = true;
            this.notifyIsTyping();
            browser.clearTimeout(this._typingNotifiedTimeout);
            this._typingNotifiedTimeout = browser.setTimeout(
                () => (this.typingNotified = false),
                LONG_TYPING,
            );
        }
        this.stopTypingDebounced();
    },
    async sendMessage() {
        await super.sendMessage();
        this.stopTyping();
    },
    stopTyping() {
        browser.clearTimeout(this._typingNotifiedTimeout);
        this.typingNotified = false;
        if (this.serverKnowsTyping) {
            this.serverKnowsTyping = false;
            this.notifyIsTyping(false);
        }
    },
    /**
     * @param {string} str
     * @returns {boolean|undefined}
     */
    addEmoji(str) {
        const res = super.addEmoji(str);
        this.updateTypingState();
        return res;
    },
});
