import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { addLoadingEffect } from "@web/core/utils/ui";

export class Signup extends Interaction {
    static selector = ".oe_signup_form, .oe_reset_password_form";

    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
        ".o_password_visibility_toggle": { "t-on-click": this.onTogglePassword },
        ".o_password_visibility_toggle i": {
            "t-att-class": (el) => ({
                "fa-eye": !this.isPasswordVisible(el),
                "fa-eye-slash": this.isPasswordVisible(el),
            }),
        },
    };

    setup() {
        this.passwordVisibilityMap = {};
    }

    onSubmit() {
        const submitEl = this.el.querySelector('.oe_login_buttons > button[type="submit"]');
        if (submitEl && !submitEl.disabled) {
            const removeLoadingEffect = addLoadingEffect(submitEl);
            this.registerCleanup(removeLoadingEffect);
        }
    }

    onTogglePassword(ev) {
        const button = ev.currentTarget;
        const targetId = button.dataset.target;
        const input = this.el.querySelector(`#${targetId}`);
        input.type = input.type === "password" ? "text" : "password";
        this.passwordVisibilityMap[targetId] = input.type === "text";
    }

    isPasswordVisible(el) {
        const button = el.parentElement;
        const targetId = button.dataset.target;
        return this.passwordVisibilityMap[targetId];
    }
}

registry
    .category("public.interactions")
    .add("auth_signup.signup", Signup);
