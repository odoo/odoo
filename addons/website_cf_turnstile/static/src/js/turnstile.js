/** @odoo-module **/

import "@website/snippets/s_website_form/000";  // force deps
import publicWidget from '@web/legacy/js/public/public_widget';
import { session } from "@web/session";

export const turnStile = {
    addTurnstile: function (action) {
        if (!this.isEditable && !this.$(".s_turnstile").length) {
            const mode = new URLSearchParams(window.location.search).get('cf') == 'show' ? 'always' : 'interaction-only';
            return $(`<div class="s_turnstile cf-turnstile float-end"
                        style="display: none;"
                        data-action="${action}"
                        data-appearance="${mode}"
                        data-response-field-name="turnstile_captcha"
                        data-sitekey="${session.turnstile_site_key}"
                        data-error-callback="throwTurnstileError"
                        data-callback="turnstileSuccess"
                        data-before-interactive-callback="turnstileBecomeVisible"
                ></div>
                <script class="s_turnstile">
                    // Rethrow the error, or we only will catch a "Script error" without any info
                    // because of the script api.js originating from a different domain.
                    function throwTurnstileError(code) {
                        const error = new Error("Turnstile Error");
                        error.code = code;
                        throw error;
                    }
                    function turnstileSuccess() {
                        const form = this.wrapper.parentElement.parentElement;
                        const spinner = form.querySelector("i.turnstile-spinner");
                        const button = spinner.parentElement;
                        button.disabled = false;
                        button.classList.remove('disabled');
                        spinner.remove();
                    }
                    function turnstileBecomeVisible() {
                        this.wrapper.parentElement.style.display = '';
                    }
                </script>
                <script class="s_turnstile" src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>
            `);
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
