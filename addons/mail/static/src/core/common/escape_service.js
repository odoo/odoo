import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} EscapeEntry
 * @property {number} [priority] Higher value wins first.
 * @property {() => boolean} [isActive]
 * @property {(ev: KeyboardEvent) => boolean | void} onEscape
 */

export const mailEscapeService = {
    dependencies: ["ui"],
    start(env, { ui }) {
        /** @type {Array<EscapeEntry & { order: number }>} */
        const entries = [];
        let nextOrder = 0;

        function add(entry) {
            const item = {
                priority: entry.priority ?? 0,
                isActive: entry.isActive,
                onEscape: entry.onEscape,
                order: nextOrder++,
            };
            entries.push(item);
            return () => {
                const idx = entries.indexOf(item);
                if (idx >= 0) {
                    entries.splice(idx, 1);
                }
            };
        }

        function getCandidates() {
            return entries
                .filter((entry) => !entry.isActive || entry.isActive())
                .sort((a, b) =>
                    a.priority === b.priority ? b.order - a.order : b.priority - a.priority
                );
        }

        function onKeydown(ev) {
            if (ev.key !== "Escape" || ui.isBlocked) {
                return;
            }
            for (const entry of getCandidates()) {
                const handled = entry.onEscape?.(ev);
                if (handled !== false) {
                    ev.preventDefault();
                    ev.stopImmediatePropagation();
                    return;
                }
            }
        }

        browser.addEventListener("keydown", onKeydown, { capture: true });
        return { add };
    },
};

registry.category("services").add("mail.escape", mailEscapeService);
