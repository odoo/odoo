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
            const turnstileElement = document.createElement("div");
            turnstileElement.className = "s_turnstile cf-turnstile float-end";
            turnstileElement.dataset.action = "website_form";
            turnstileElement.dataset.appearance = mode;
            turnstileElement.dataset.responseFieldName = "turnstile_captcha";
            turnstileElement.dataset.sitekey = session.turnstile_site_key;
            turnstileElement.dataset.errorCallback = "throwTurnstileError";

            const scriptElement1 = document.createElement("script");
            scriptElement1.className = "s_turnstile";
            scriptElement1.textContent = `
                // Rethrow the error, or we only will catch a "Script error" without any info
                // because of the script api.js originating from a different domain.
                function throwTurnstileError(code) {
                    const error = new Error("Turnstile Error");
                    error.code = code;
                    throw error;
                }
            `;

            const scriptElement2 = document.createElement("script");
            scriptElement2.className = "s_turnstile";
            scriptElement2.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";

            const formSendElement = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            formSendElement.parentNode.insertBefore(turnstileElement, formSendElement.nextSibling);
            formSendElement.parentNode.insertBefore(scriptElement1, formSendElement.nextSibling);
            formSendElement.parentNode.insertBefore(scriptElement2, formSendElement.nextSibling);
        }
        return res;
    },

    /**
     * Remove potential existing loaded script/token
    */
    cleanTurnstile: function () {
        const turnstileElements = this.el.querySelectorAll(".s_turnstile");
        turnstileElements.forEach(element => element.remove());
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
