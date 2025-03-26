import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { isMarkup } from "../../../utils/common/format";
import { registry } from "@web/core/registry";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";

const commandRegistry = registry.category("discuss.channel_commands");

patch(Thread.prototype, {
    onPinStateUpdated() {
        super.onPinStateUpdated();
        if (!this.displayToSelf && !this.isLocallyPinned && this.eq(this.store.discuss.thread)) {
            if (this.store.discuss.isActive) {
                const newThread =
                    this.store.discuss.channels.threads.find(
                        (thread) => thread.displayToSelf || thread.isLocallyPinned
                    ) || this.store.inbox;
                newThread.setAsDiscussThread();
            } else {
                this.store.discuss.thread = undefined;
            }
        }
    },
    /** @param {string} body */
    async post(body) {
        let textContent = body;
        if (isMarkup(body)) {
            textContent = createDocumentFragmentFromContent(body).body.textContent;
        }
        if (this.model === "discuss.channel" && textContent.startsWith("/")) {
            const [firstWord] = textContent.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.channel_types || command.channel_types.includes(this.channel_type))
            ) {
                await this.executeCommand(command, textContent);
                return;
            }
        }
        return super.post(...arguments);
    },
});
