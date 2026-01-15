import { useEnv, useExternalListener, useState, useSubEnv } from "@odoo/owl";

function isSmall() {
    return window.innerWidth < 960;
}

export function useDocUI() {
    const env = useEnv();
    if (env.ui) {
        return useState(env.ui);
    }
    const ui = useState({
        isSmall: isSmall(),
        size: window.innerWidth,
    });

    useSubEnv({ ui });
    useExternalListener(window, "resize", () => {
        ui.size = window.innerWidth;
        ui.isSmall = isSmall();
    });

    return ui;
}
