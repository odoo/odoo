import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class AccessErrorNotification extends Interaction {
    static selector = ".o_portal_my_home, .oe_login_form";

    start() {
        const params = new URLSearchParams(window.location.search);
        if (params.has("access_error")) {
            this.services.notification.add(
                _t("This page is no longer accessible. Please ask your contact for a new link."),
                { type: "danger", sticky: true },
            );
            const url = new URL(window.location.href);
            url.searchParams.delete("access_error");
            window.history.replaceState({}, document.title, url.href);
        }
    }
}

registry
    .category("public.interactions")
    .add("project.access_error_notification", AccessErrorNotification);
