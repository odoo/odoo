import { useState, onWillStart, onWillDestroy } from "@odoo/owl";

export function useRegistry(registry) {
    const state = useState({ entries: registry.getEntries() });
    const listener = ({ detail }) => {
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
    };

    onWillStart(() => registry.addEventListener("UPDATE", listener));
    onWillDestroy(() => registry.removeEventListener("UPDATE", listener));
    return state;
}
