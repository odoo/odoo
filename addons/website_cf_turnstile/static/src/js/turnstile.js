/** @odoo-module **/

import "@website/snippets/s_website_form/000";  // force deps
import publicWidget from '@web/legacy/js/public/public_widget';
import { session } from "@web/session";

publicWidget.registry.s_website_form.include({
    /**
     * @override
    */
    start: function () {
        const res = this._super(...arguments);
        this.cleanTurnstile();
        if (!this.isEditable && !this.el.querySelector(".s_turnstile") && session.turnstile_site_key) {
            const mode = new URLSearchParams(window.location.search).get("cf") == "show" ? "always" : "interaction-only";
            const turnstileEl = document.createElement("div");
            turnstileEl.className = "s_turnstile cf-turnstile float-end";
            turnstileEl.dataset.action = "website_form";
            turnstileEl.dataset.appearance = mode;
            turnstileEl.dataset.responseFieldName = "turnstile_captcha";
            turnstileEl.dataset.sitekey = session.turnstile_site_key;
            turnstileEl.dataset.errorCallback = "throwTurnstileError";

            const script1El = document.createElement("script");
            script1El.className = "s_turnstile";
            script1El.textContent = `
                // Rethrow the error, or we only will catch a "Script error" without any info
                // because of the script api.js originating from a different domain.
                function throwTurnstileError(code) {
                    const error = new Error("Turnstile Error");
                    error.code = code;
                    throw error;
                }
            `;

            const script2El = document.createElement("script");
            script2El.className = "s_turnstile";
            script2El.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";

            const formSendEl = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            formSendEl.parentNode.insertBefore(turnstileEl, formSendEl.nextSibling);
            formSendEl.parentNode.insertBefore(script1El, formSendEl.nextSibling);
            formSendEl.parentNode.insertBefore(script2El, formSendEl.nextSibling);
        }
        return res;
    },

    /**
     * Remove potential existing loaded script/token
    */
    cleanTurnstile: function () {
        const turnstileEls = this.el.querySelectorAll(".s_turnstile");
        turnstileEls.forEach(element => element.remove());
    },

    /**
     * @override
     * Discard all library changes to reset the state of the Html.
    */
    destroy: function () {
        this.cleanTurnstile();
        this._super(...arguments);
    },
});
