import { _t } from "@web/core/l10n/translation";

/**
 * Initialize Local Network Access permission handling.
 *
 * @returns {Promise<{
 *  type: "warning" | "danger" | "success" | "info"
 *  message: string
 * }>}
 */
export const initLNA = async (notificationService, callback = () => {}) => {
    const processLNAState = (result) => {
        let type = "";
        let message = "";

        if (result.state === "granted") {
            type = "success";
            message = _t("Local Network Access permission granted.");
        } else if (result.state === "prompt") {
            type = "warning";
            message = _t(
                "Local Network Access permission is not yet granted. Some hardware devices might not work properly. Please allow Local Network Access in your browser settings."
            );
        } else {
            type = "danger";
            message = _t(
                "Local Network Access permission is denied. Some hardware devices might not work properly. Please allow Local Network Access in your browser settings."
            );
            notificationService.add(message, { type: "warning" });
        }

        callback(type, message);
    };

    try {
        const result = await navigator.permissions.query({ name: "local-network-access" });
        processLNAState(result);
        result.onchange = () => processLNAState(result);
    } catch {
        const isChromiumBased = navigator.userAgent.includes("Chromium") || !!window.chrome;
        let message;
        if (!isChromiumBased) {
            message = _t(
                "Local Network Access configuration is enabled, but your browser is not Chromium-based. Please use a Chromium-based browser to benefit from this feature. Please note that IOS devices do not support Local Network Access yet."
            );
        } else {
            message = _t(
                "Local Network Access is enabled for this POS, but your browser version does not support it. Please update your browser to the latest version."
            );
        }

        notificationService.add(message, { type: "warning" });
        callback("danger", message);
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

// Checks whether an ip address is on the local network. So one of the ranges:
// 10.0.0.0 - 10.255.255.255
// 127.0.0.0 - 127.255.255.255
// 172.16.0.0 - 172.31.255.255
// 169.254.0.0 - 169.254.255.255
// 192.168.0.0 - 192.168.255.255
export function isPrivateIp(ip) {
    if (!ip || typeof ip !== "string") {
        return false;
    }
    const blocks = ip.split(".");
    if (blocks.length !== 4) {
        return false;
    }

    const [a, b, c, d] = blocks.map(Number);
    const invalidBlock = blocks.some(
        (b, i) => isNaN([a, b, c, d][i]) || [a, b, c, d][i] < 0 || [a, b, c, d][i] > 255
    );

    if (invalidBlock) {
        return false;
    }

    return (
        a === 10 ||
        a === 127 ||
        (a === 172 && b >= 16 && b <= 31) ||
        (a === 192 && b === 168) ||
        (a === 169 && b === 254)
    );
}

const LOCAL_URL_CACHE = new Map();
const MAX_CACHE_ENTRIES = 50;

export function isLocalHTTP(url) {
    try {
        const hit = LOCAL_URL_CACHE.get(url);
        if (hit !== undefined) {
            return hit;
        }
        const u = new URL(url);
        const result = u.protocol === "http:" && isPrivateIp(u.hostname);
        LOCAL_URL_CACHE.set(url, result);
        if (LOCAL_URL_CACHE.size > MAX_CACHE_ENTRIES) {
            LOCAL_URL_CACHE.delete(LOCAL_URL_CACHE.keys().next().value);
        }
        return result;
    } catch {
        return false;
    }
}
