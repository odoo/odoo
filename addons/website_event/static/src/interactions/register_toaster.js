import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class RegisterToaster extends Interaction {
    static selector = ".o_wevent_register_toaster";

    setup() {
        const message = this.el.dataset.message;
        if (message && message.length) {
            this.services.notification.add(message, {
                title: _t("Register"),
                type: 'info',
            });
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event.register_toaster", RegisterToaster);
