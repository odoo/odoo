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
            !this.el.querySelector(".s_turnstile")
            && session.turnstile_site_key
        ) {
            this.uniq = uniqueId("turnstile_");
            this.el.classList.add(this.uniq);
            const { turnstileEl, script1El, script2El, inputValidation } = new TurnStile(
                "website_form",
                `.${this.uniq} .s_website_form_send,.${this.uniq} .o_website_form_send`,
            );
            const formSendEl = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            if (!formSendEl.classList.contains('disabled') && !formSendEl.classList.contains('no_auto_disable')) {
                formSendEl.classList.add('disabled', 'cf_form_disabled');
            }
            formSendEl.parentNode.insertBefore(turnstileEl, formSendEl);
            formSendEl.parentNode.insertBefore(script1El, formSendEl.nextSibling);
            formSendEl.parentNode.insertBefore(script2El, formSendEl.nextSibling);
            formSendEl.parentNode.insertBefore(inputValidation, formSendEl.nextSibling);
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
