import { Form } from "@website/snippets/s_website_form/form";
import { patch } from "@web/core/utils/patch";

import { uniqueId } from "@web/core/utils/functions";
import { session } from "@web/session";
import { TurnStile } from "./turnstile";

patch(Form.prototype, {
    /**
     * @override
     */
    start() {
        super.start();
        TurnStile.clean(this.el);
        if (
            !this.el.classList.contains("s_website_form_no_recaptcha") &&
            !this.el.querySelector(".s_turnstile") &&
            session.turnstile_site_key
        ) {
            this.uniq = uniqueId("turnstile_");
            this.el.classList.add(this.uniq);
            const turnstile = new TurnStile("website_form");
            const formSendEl = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            TurnStile.disableSubmit(formSendEl);
            formSendEl.parentNode.insertBefore(turnstile.turnstileEl, formSendEl);
            turnstile.insertScripts(this.el);
            turnstile.render();
        }
    },

    /**
     * Discard all library changes to reset the state of the Html.
     * @override
     */
    destroy() {
        TurnStile.clean(this.el);
        super.destroy();
    },
});
