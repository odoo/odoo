import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ShowPassword extends Interaction {
    static selector = ".show-password";
    dynamicContent = {
        _root: { "t-on-pointerdown": this.showText },
    };

    setup() {
        const inputGroupEl = this.el.closest(".input-group");
        this.passwordEl = inputGroupEl.querySelector("input[type='password']");
        this.iconEl = inputGroupEl.querySelector("i");
    }

    showText() {
        this.passwordEl.type = "text";
        this.iconEl.classList.replace("fa-eye", "fa-eye-slash");
        document.body.addEventListener(
            "pointerup",
            () => {
                this.passwordEl.type = "password";
                this.iconEl.classList.replace("fa-eye-slash", "fa-eye");
            },
            { once: true }
        );
    }
}

registry.category("public.interactions").add("web.show_password", ShowPassword);
