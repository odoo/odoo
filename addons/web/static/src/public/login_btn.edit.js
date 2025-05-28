import { Interaction } from "./interaction";
import { registry } from "@web/core/registry";

export class LoginBtnEdit extends Interaction {
    static selector = ".oe_login_form";
    dynamicContent = {
        "a": { "t-on-click": this.onClick },
        "button": { "t-on-click": this.onClick },
    };

    onClick(ev) {
        ev.preventDefault();
    }
}

registry.category("public.interactions.edit").add("website.login_btn", {
    Interaction: LoginBtnEdit,
});

