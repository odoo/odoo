/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
const log = makeLogger("pos.lna");
/**
 * @param {object} notificationService
 * @param {(type: string, message: string) => void} [callback]
 * @param {{ signal?: AbortSignal, watch?: boolean }} [options]
 * @returns {Promise<void>}
 */
export const initLNA = async (
    notificationService,
    callback = () => {},
    { signal, watch = true } = {},
) => {
    if (signal?.aborted) {
        return;
    }
    log.lifecycle("initLNA", () => ({ useLna: Boolean(odoo.use_lna) }));
    if (!odoo.use_lna) {
        callback("info", _t("Local Network Access is not configured for this POS."));
        return;
    }

    const processLNAState = (result) => {
        if (signal?.aborted) {
            return;
        }
        let type;
        let message;
        log.logic("processLNAState", () => ({ state: result.state }));

        if (result.state === "granted") {
            type = "success";
            message = _t("Local Network Access permission granted.");
        } else if (result.state === "prompt") {
            type = "warning";
            message = _t(
                "Local Network Access permission is not yet granted. Some hardware devices might not work properly. Please allow Local Network Access in your browser settings.",
            );
        } else {
            type = "danger";
            message = _t(
                "Local Network Access permission is denied. Some hardware devices might not work properly. Please allow Local Network Access in your browser settings.",
            );
            notificationService.add(message, { type: "warning" });
        }

        callback(type, message);
    };

    let result;
    try {
        result = await navigator.permissions.query({ name: "local-network-access" });
    } catch {
        if (signal?.aborted) {
            return;
        }
        odoo.use_lna = false;
        const isChromiumBased =
            navigator.userAgent.includes("Chromium") || !!window.chrome;
        log.logic("permission query unsupported, LNA disabled", () => ({
            isChromiumBased,
        }));
        let message;
        if (!isChromiumBased) {
            message = _t(
                "Local Network Access configuration is enabled, but your browser is not Chromium-based. Please use a Chromium-based browser to benefit from this feature. Please note that IOS devices do not support Local Network Access yet.",
            );
        } else {
            message = _t(
                "Local Network Access is enabled for this POS, but your browser version does not support it. Please update your browser to the latest version.",
            );
        }

        notificationService.add(message, { type: "warning" });
        callback("danger", message);
        return;
    }

    processLNAState(result);
    if (watch && !signal?.aborted) {
        result.addEventListener("change", () => processLNAState(result), { signal });
    }
};

export function getLNATargetAddressSpace(url) {
    let hostname;
    try {
        hostname = new URL(url).hostname;
    } catch {
        hostname = url;
    }
    if (hostname === "localhost" || hostname === "127.0.0.1") {
        return "loopback";
    }
    return "local";
}
