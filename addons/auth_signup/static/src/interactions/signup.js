import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { addLoadingEffect } from "@web/core/utils/ui";

export class Signup extends Interaction {
    static selector = ".oe_signup_form, .oe_reset_password_form";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
    };

    onSubmit() {
        const submitEl = this.el.querySelector('.oe_login_buttons > button[type="submit"]');
        if (submitEl && !submitEl.disabled) {
            const removeLoadingEffect = addLoadingEffect(submitEl);
            this.registerCleanup(removeLoadingEffect);
        }
    }
}

registry
    .category("public.interactions")
    .add("auth_signup.signup", Signup);
