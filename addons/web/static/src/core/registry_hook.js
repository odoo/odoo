import { useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

/**
 * Get the entries of a registry and update the state when the registry is updated.
 * @param {import('./registry').Registry} registry
 * @returns {{ entries: [string, any][] }} the entries of the registry, as a reactive state
 */
export function useRegistry(registry) {
    const state = useState({ entries: registry.getEntries() });
    useBus(registry, "UPDATE", ({ detail }) => {
        const index = state.entries.findIndex(([k]) => k === detail.key);
        if (detail.operation === "add" && index === -1) {
            // push the new entry at the right place
            const newEntries = registry.getEntries();
            const newEntry = newEntries.find(([k]) => k === detail.key);
            const newIndex = newEntries.indexOf(newEntry);
            if (newIndex === newEntries.length - 1) {
                state.entries.push(newEntry);
            } else {
                state.entries.splice(newIndex, 0, newEntry);
            }
        } else if (detail.operation === "delete" && index >= 0) {
            state.entries.splice(index, 1);
        }
    });
    return state;
}
