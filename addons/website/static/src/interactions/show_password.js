import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ShowPassword extends Interaction {
    static selector = "#showPass";
    dynamicContent = {
        _root: { "t-on-pointerdown": this.showText },
    };

    setup() {
        this.passwordEl = this.el.closest(".input-group").querySelector("#password");
    }

    showText() {
        this.passwordEl.setAttribute("type", "text");
        this.addListener(
            document.body,
            "pointerup",
            () => this.passwordEl.setAttribute("type", "password"),
            { once: true },
        );
    }
}

registry
    .category("public.interactions")
    .add("website.show_password", ShowPassword);
