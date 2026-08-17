import { onWillUnmount, signal } from "@odoo/owl";

const ancestors = signal.Object({});

/**
 * @returns {{ ancestors: () => Record<string, boolean>, register: (name: string) => void }}
 */
export function useHasAncestor() {
    return {
        ancestors,
        register(name) {
            ancestors()[name] = true;
            onWillUnmount(() => delete ancestors()[name]);
        },
    };
}
