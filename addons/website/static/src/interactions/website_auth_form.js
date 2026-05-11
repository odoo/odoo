import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Interaction } from "@web/public/interaction";
import { session } from "@web/session";

export class WebsiteAuthFormWarning extends Interaction {
    static selector = "form:is(.oe_signup_form, .oe_login_form)";
    dynamicContent = {
        ".oe_login_buttons > button[type='submit']": {
            "t-att-disabled": () => !session.is_public,
        },
    };

    start() {
        if (!session.is_public) {
            const btnWrapperEl = this.el.querySelector(".oe_login_buttons");
            const warningEl = document.createElement("p");
            warningEl.className = "alert alert-warning";
            warningEl.setAttribute("role", "alert");
            warningEl.textContent = this.el.classList.contains("oe_signup_form")
                ? _t("You are already signed in.")
                : _t("You are already logged in.");
            this.insert(warningEl, btnWrapperEl, "afterbegin");
        }
    }
}

registry.category("public.interactions").add("website.auth_form", WebsiteAuthFormWarning);
