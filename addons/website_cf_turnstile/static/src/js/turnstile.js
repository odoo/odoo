/** @odoo-module **/

import "@website/snippets/s_website_form/000";  // force deps
import publicWidget from '@web/legacy/js/public/public_widget';
import { renderToElement } from "@web/core/utils/render";
import { session } from "@web/session";

export const turnStile = {
    addTurnstile: function (action) {
        if (!this.isEditable && !this.$(".s_turnstile").length) {
            const mode = new URLSearchParams(window.location.search).get('cf') == 'show' ? 'always' : 'interaction-only';
            const turnstileContainer = renderToElement("website_cf_turnstile.turnstile_container", {
                action: action,
                appearance: mode,
                additionalClasses: "float-end",
                beforeInteractiveGlobalCallback: "turnstileBecomeVisible",
                errorGlobalCallback: "throwTurnstileErrorCode",
                executeGlobalCallback: "turnstileSuccess",
                sitekey: session.turnstile_site_key,
                style: "display: none;",
            });
            const turnstileScript = renderToElement("website_cf_turnstile.turnstile_remote_script");
            // Rethrow the error, or we only will catch a "Script error" without any info 
            // because of the script api.js originating from a different domain.
            globalThis.throwTurnstileError = (code) => {
                const error = new Error("Turnstile Error");
                error.code = code;
                throw error;
            }
            globalThis.turnstileSuccess = () => {
                    const form = turnstileContainer.parentElement;
                    const spinner = form.querySelector("i.turnstile-spinner");
                    const button = spinner.parentElement;
                    button.disabled = false;
                    button.classList.remove('disabled');
                    spinner.remove();
            };
            globalThis.turnstileBecomeVisible = () => {
                turnstileContainer.style.display = '';
            }
            return $(turnstileContainer).add($(turnstileScript))
        }
    },

    /**
     * Remove potential existing loaded script/token
     */
    cleanTurnstile: function () {
        if (this.$(".s_turnstile").length) {
            this.$(".s_turnstile").remove();
        }
    },

    /**
     * @override
     * Discard all library changes to reset the state of the Html.
     */
    destroy: function () {
        this.cleanTurnstile();
        this._super(...arguments);
    },

    addSpinner(button) {
        const spinner = document.createElement("i");
        spinner.classList.add("fa", "fa-refresh", "fa-spin", "turnstile-spinner");
        button.innerText = " " + button.innerText;
        button.disabled = true;
        button.classList.add("disabled");
        button.prepend(spinner);
    },
};

const signupTurnStile = {
    ...turnStile,

    async willStart() {
        this._super(...arguments);
        if (!session.turnstile_site_key) {
            return;
        }
        const button = this.el.querySelector('button[type="submit"]');
        this.addSpinner(button);
        this.cleanTurnstile();
        this.addTurnstile(this.action)?.insertBefore(button);
    },
};

publicWidget.registry.s_website_form.include({
    ...turnStile,

    /**
     * @override
     */
    start: function () {
        const res = this._super(...arguments);
        if (session.turnstile_site_key) {
            const button = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            this.addSpinner(button);
            this.cleanTurnstile();
            this.addTurnstile("website_form")?.insertAfter(button);
        }
        return res;
    },
});

publicWidget.registry.turnstileCaptchaSignup = publicWidget.Widget.extend({
    ...signupTurnStile,
    selector: ".oe_signup_form",
    action: "signup",
});

publicWidget.registry.turnstileCaptchaPasswordReset = publicWidget.Widget.extend({
    ...signupTurnStile,
    selector: ".oe_reset_password_form",
    action: "password_reset",
});
