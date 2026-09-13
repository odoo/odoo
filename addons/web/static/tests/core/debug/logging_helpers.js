// @ts-check

import {
    disableLogging,
    enableLogging,
    getStatus,
    resetStats,
} from "@web/core/debug/debug_logger";

/** @returns {() => void} */
export function isolateLogging() {
    const { spec } = getStatus();
    resetStats();
    return () => {
        if (spec) {
            enableLogging(spec, { persist: false });
        } else {
            disableLogging({ persist: false });
        }
        resetStats();
    };
}
