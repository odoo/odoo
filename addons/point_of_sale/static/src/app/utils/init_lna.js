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
    if (!odoo.use_lna) {
        callback("info", _t("Local Network Access is not configured for this POS."));
        return;
    }

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
        odoo.use_lna = false;
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
