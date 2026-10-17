import { Component, onWillDestroy, signal, useApp, useEffect, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { CriticalPOSError } from "./critical_pos_error/critical_pos_error";

export class Loader extends Component {
    static template = "point_of_sale.Loader";
    props = useProps({ loader: t.object({ isShown: t.boolean(), error: t.object() }) });
    static components = { CriticalPOSError };

    setup() {
        const app = useApp();
        this.message = signal("");
        const timeout = setTimeout(
            () => this.message.set(_t("Still loading, thank you for your patience…")),
            8000
        );
        onWillDestroy(() => clearTimeout(timeout));
        useEffect(() => {
            if (!this.props.loader.isShown) {
                // Destroy the loader app after it has faded out
                setTimeout(() => app.destroy(), 400);
            }
        });
    }
}
