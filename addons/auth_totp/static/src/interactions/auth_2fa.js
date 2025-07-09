import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Auth2FABtnDisable extends Interaction {
    static selector = ".o_auth_2fa_btn_disable";

    dynamicContent = {
        root: {
            "t-on-mouseover": (ev) => {
                console.log("pass inside o_auth_2fa_btn_disable");
            },
        },
    };

    setup() {
        this.originalContent = this.el.textContent;
    }

}

registry
    .category("public.interactions")
    .add("auth.auth_2fa_btn_disable", Auth2FABtnDisable);