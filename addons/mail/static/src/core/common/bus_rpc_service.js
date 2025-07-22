import { Deferred } from "@bus/workers/websocket_worker_utils";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { uuid } from "@web/core/utils/strings";

/**
 * Service that wraps RPC calls to coordinate with bus notifications.
 * Ensures the client waits for both the RPC response and the corresponding
 * bus notifications.
 */
export const busRpcService = {
    dependencies: ["bus_service"],
    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, { bus_service: busService }) {
        const uuidToDeferred = new Map();
        busService.subscribe("bus_rpc/end", (uuid) => uuidToDeferred.get(uuid)?.resolve());
        return async function busRpc(url, params = {}, settings = {}) {
            const requestId = uuid();
            const deferred = new Deferred();
            uuidToDeferred.set(requestId, deferred);
            params["bus_rpc_uuid"] = requestId;
            try {
                const result = await rpc(url, params, settings);
                await deferred;
                return result;
            } finally {
                uuidToDeferred.delete(requestId);
            }
        };
    },
};

registry.category("services").add("mail.busRpc", busRpcService);
