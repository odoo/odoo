import { proxy, useListener } from "@odoo/owl";
import { useEnv, useSubEnv } from "@web/owl2/utils";

function isSmall() {
    return window.innerWidth < 960;
}

export function useDocUI() {
    const env = useEnv();
    if (env.ui) {
        return proxy(env.ui);
    }
    const ui = proxy({
        isSmall: isSmall(),
        size: window.innerWidth,
    });

    useSubEnv({ ui });
    useListener(window, "resize", () => {
        ui.size = window.innerWidth;
        ui.isSmall = isSmall();
    });

    return ui;
}
