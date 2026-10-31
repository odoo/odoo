import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class ShowPassword extends Interaction {
    static selector = ".input-group";
    static selectorHas = "> .o_show_password";
    dynamicContent = {
        ".o_show_password": {
            "t-on-click": () => (this.showPassword = !this.showPassword),
            "t-att-aria-pressed": () => (this.showPassword ? "true" : "false"),
        },
        "input[type='text'], input[type='password']": {
            "t-att-type": () => (this.showPassword ? "text" : "password"),
        },
        ".o_show_password > i": {
            "t-att-data-icon": () => (this.showPassword ? "visibility_off" : "visibility"),
        },
        "[aria-live='polite']": {
            "t-out": () => (this.showPassword ? _t("Your password is shown.") : ""),
        },
    };
}

registry.category("public.interactions").add("web.show_password", ShowPassword);
