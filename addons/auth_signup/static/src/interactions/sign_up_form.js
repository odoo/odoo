import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SignUpForm extends Interaction {
    static selector = ".oe_signup_form";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
        ".oe_login_buttons > button[type='submit']": { "t-att-disabled": () => this.submitElStatus },
    };

    setup() {
        this.submitElStatus = null;
    }

    onSubmit() {
        const submitEl = document.querySelector(".oe_login_buttons > button[type='submit']");
        if (!this.submitElStatus) {
            this.submitElStatus = "disabled";
            const refreshEl = document.createElement("i");
            refreshEl.classList.add("fa", "fa-circle-o-notch", "fa-spin");
            this.insert(refreshEl, submitEl, "beforebegin");
        }
    }
}

registry
    .category("public.interactions")
    .add("auth_signup.sign_up_form", SignUpForm);
