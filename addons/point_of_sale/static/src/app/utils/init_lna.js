import { _t } from "@web/core/l10n/translation";

export const initLNA = async (notificationService) => {
    if (!odoo.use_lna) {
        return;
    }
    try {
        const result = await navigator.permissions.query({ name: "local-network-access" });
        if (["granted", "prompt"].includes(result?.state)) {
            return;
        }

        const message = _t(
            "Local Network Access permission is denied. Some hardware devices might not work properly. Please allow Local Network Access in your browser settings."
        );
        notificationService.add(message, { type: "warning" });
    } catch {
        odoo.use_lna = false;
        const isChromiumBased = navigator.userAgent.includes("Chromium") || !!window.chrome;
        let message;
        if (!isChromiumBased) {
            message = _t(
                "Local Network Access configuration is enabled, but your browser is not Chromium-based. Please use a Chromium-based browser to benefit from this feature."
            );
        } else {
            message = _t(
                "Local Network Access is enabled for this POS, but your browser version does not support it. Please update your browser to the latest version."
            );
        }
        notificationService.add(message, { type: "warning" });
    }
};
