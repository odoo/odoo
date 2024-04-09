import { mailGlobal } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

function rpcWithEnv(env) {
    return function (url, params = {}, settings = {}) {
        if (mailGlobal.isInTest && !mailGlobal.elligibleEnvs.has(env?.envId)) {
            return new Promise(() => {});
        }
        return rpc(...arguments);
    };
}

export const mailRpcService = {
    /** @param {import("@web/env").OdooEnv} env */
    start(env) {
        return rpcWithEnv(env);
    },
};

registry.category("services").add("mail.rpc", mailRpcService);
