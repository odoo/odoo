import { Component, onWillDestroy, proxy, useApp, useEffect, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { getColorScheme } from "@point_of_sale/utils";
import { CriticalPOSError } from "./critical_pos_error/critical_pos_error";

export class Loader extends Component {
    static template = "point_of_sale.Loader";
    props = useProps({ loader: t.object({ isShown: t.boolean(), error: t.object() }) });
    static components = { CriticalPOSError };

    setup() {
        const app = useApp();
        this.isDark = getColorScheme() === "dark";
        this.state = proxy({ message: "" });
        const timeout = setTimeout(
            () => (this.state.message = _t("Still loading, thank you for your patience…")),
            8000
        );
        onWillDestroy(() => clearTimeout(timeout));
        useEffect(() => {
            if (!this.props.loader.isShown) {
                // Destroy the loader app after it has faded out
                setTimeout(() => app.destroy(), 1000);
            }
        });
    }
}
