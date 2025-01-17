import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";
import { session } from "@web/session";
import { TurnStile } from "./turnstile";

export class TurnstileCaptcha extends Interaction {
    static selector = "[data-captcha]";

    async willStart() {
        TurnStile.clean(this.el);
    }

    start() {
        if (
            !this.el.querySelector(".s_turnstile")
            && session.turnstile_site_key
        ) {
            this.uniq = uniqueId("turnstile_");
            const action = this.el.dataset.captcha || "generic";
            const { turnstileEl, script1El, script2El } = new TurnStile(action, `.${this.uniq}`);
            const submitButton = this.el.querySelector("button[type='submit']");
            submitButton.classList.add(this.uniq);
            submitButton.parentNode.insertBefore(turnstileEl, submitButton);
            this.el.appendChild(script1El);
            this.el.appendChild(script2El);
        }
    }

    /**
     * Discard all library changes to reset the state of the Html.
     */
    destroy() {
        TurnStile.clean(this.el);
        super.destroy();
    }
}

registry
    .category("public.interactions")
    .add("website_cf_turnstile.turnstile_captcha", TurnstileCaptcha);
