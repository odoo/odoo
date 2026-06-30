import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ShowPassword extends Interaction {
    static selector = ".input-group";
    static selectorHas = ":scope > .o_show_password";
    dynamicContent = {
        ".o_show_password": {
            "t-on-click": () => this.showPassword = !this.showPassword,
        },
        "input[type='text'], input[type='password']": {
            "t-att-type": () => this.showPassword ? "text" : "password",
        },
        ".o_show_password > i": {
            "t-att-class": () => ({
                "fa-eye": !this.showPassword,
                "fa-eye-slash": !!this.showPassword,
            }),
        },
    };
}

registry.category("public.interactions").add("web.show_password", ShowPassword);
