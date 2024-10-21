/** @odoo-module **/

import "@website/snippets/s_website_form/000";  // force deps
import publicWidget from '@web/legacy/js/public/public_widget';
import { session } from "@web/session";


const injectTurnstile = (actionName, className) => {
    const mode = new URLSearchParams(window.location.search).get('cf') == 'show' ? 'always' : 'interaction-only';
    
    $(`<div class="s_turnstile cf-turnstile float-end"
            data-action="${actionName}"
            data-appearance="${mode}"
            data-response-field-name="turnstile_captcha"
            data-sitekey="${session.turnstile_site_key}"
            data-error-callback="throwTurnstileError"
        ></div>
        <script class="s_turnstile">
            // Rethrow the error, or we only will catch a "Script error" without any info 
            // because of the script api.js originating from a different domain.
            function throwTurnstileError(code) {
                const error = new Error("Turnstile Error");
                error.code = code;
                throw error;
            }
        </script>
        <script class="s_turnstile" src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>
    `).insertAfter(className);
}


publicWidget.registry.subscribe.include({
    _updateView(data) {
        const res = this._super(...arguments);
        // Hide captcha if user is already subscribed
        this.cleanTurnstile();
        console.log("newsletter", this.isEditable, this.$(".s_turnstile"), session);
        if (!this.isEditable && !this.$('.s_turnstile').length && session.turnstile_site_key && !data.is_subscriber) {
            injectTurnstile("website_mass_mailing_subscribe", '.s_newsletter_subscribe_form', this.el);
        }
        return res;
    },
    _getCaptchaData: async () => {
        const tokenEl = document.querySelector(`input[name="turnstile_captcha"]`);
        return {
            error: !tokenEl.value ? "Cloudflare human verification failed" : null,
            field: {
                "turnstile_captcha": tokenEl.value,
            }
        }
    },
    /**
     * Remove potential existing loaded script/token
     */
    cleanTurnstile: function () {
        if (this.$('.s_turnstile').length) {
            this.$('.s_turnstile').remove();
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
})

publicWidget.registry.s_website_form.include({
    /**
     * @override
     */
    start: function () {
        const res = this._super(...arguments);
        this.cleanTurnstile();
        console.log("websiteform", this.isEditable, this.$(".s_turnstile"), session);

        if (!this.isEditable && !this.$('.s_turnstile').length && session.turnstile_site_key) {
            injectTurnstile("website_form", '.s_website_form_send, .o_website_form_send', this.el);
        }
        return res;
    },
    /**
     * Remove potential existing loaded script/token
     */
    cleanTurnstile: function () {
        if (this.$('.s_turnstile').length) {
            this.$('.s_turnstile').remove();
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
});
