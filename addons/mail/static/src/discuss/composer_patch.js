/* @odoo-module */

import { Composer } from "@mail/composer/composer";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

patch(Composer.prototype, "discuss", {
    /**
     * @override
     */
    onInput(ev) {
        if (this.thread?.model === "discuss.channel" && ev.target.value.startsWith("/")) {
            const [firstWord] = ev.target.value.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                ev.target.value === "/" || // suggestions not yet started
                this.hasSuggestions ||
                (command &&
                    (!command.channel_types || command.channel_types.includes(this.thread.type)))
            ) {
                this.stopTyping();
                return;
            }
        }
        this._super(ev);
    },
});
