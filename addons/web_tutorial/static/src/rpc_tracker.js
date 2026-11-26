import { computed, effect, signal, untrack, useListener } from "@odoo/owl";
import { rpcBus } from "@web/core/network/rpc";

/**
 * Tracks the pending RPCs, but the ones on the ignored model (e.g. all the
 * ones on the tutorials, saving the progress among them)
 * @param {string} ignoredModel
 */
export function useRpcTracker(ignoredModel) {
    const pendingIds = signal.Set(new Set());
    const isPending = computed(() => pendingIds().size > 0);
    useListener(rpcBus, "RPC:REQUEST", (ev) =>
        untrack(() => {
            if (ev.detail.data.params?.model !== ignoredModel) {
                pendingIds().add(ev.detail.data.id);
            }
        })
    );
    useListener(rpcBus, "RPC:RESPONSE", (ev) => untrack(() => pendingIds().delete(ev.detail.data.id)));
    return {
        /** Whether some RPCs are pending */
        isPending,
        /**
         * @returns {Promise<void>} resolved once no RPC is pending anymore, and
         *   the web client rendered their results (e.g. a kanban view its new
         *   column, its response only being processed after its RPC ended)
         */
        async waitForIdle() {
            while (isPending()) {
                let stop;
                await new Promise((resolve) => (stop = effect(() => !isPending() && resolve())));
                stop();
                await new Promise((resolve) => requestAnimationFrame(resolve));
            }
        },
    };
}
