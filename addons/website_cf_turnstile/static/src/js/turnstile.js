import "@website/snippets/s_website_form/000";  // force deps
import { uniqueId } from "@web/core/utils/functions";
import publicWidget from '@web/legacy/js/public/public_widget';
import { session } from "@web/session";


const turnStile = {
    addTurnstile(action, selector) {
        const cf = new URLSearchParams(window.location.search).get("cf");
        const mode = cf == "show" ? "always" : "interaction-only";
        const turnstileEl = document.createElement("div");
        turnstileEl.className = "s_turnstile cf-turnstile";
        turnstileEl.dataset.action = action;
        turnstileEl.dataset.appearance = mode;
        turnstileEl.dataset.responseFieldName = "turnstile_captcha";
        turnstileEl.dataset.sitekey = session.turnstile_site_key;
        turnstileEl.dataset.callback = "turnstileCallback";
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

            function turnstileCallback() {
                const btnEl = document.querySelector('${selector}');
                if (btnEl && btnEl.classList.contains('cf_form_disabled')) {
                    btnEl.classList.remove('disabled', 'cf_form_disabled');
                }
                btnEl.closest('form').querySelector("input.turnstile_captcha_valid').value = 'done';
            }
        `;

        const script2El = document.createElement("script");
        script2El.className = "s_turnstile";
        script2El.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";

        // avoid autosubmit from password manager
        const inputValidation = document.createElement("input");
        inputValidation.style = 'display: none;';
        inputValidation.className = 'turnstile_captcha_valid';
        inputValidation.required = true;

        return [turnstileEl, script1El, script2El, inputValidation];
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
};

publicWidget.registry.s_website_form.include({
    ...turnStile,

    /**
     * @override
    */
    start() {
        const res = this._super(...arguments);
        this.cleanTurnstile();
        if (
            !this.isEditable &&
            !this.el.querySelector(".s_turnstile") &&
            session.turnstile_site_key
        ) {
            this.uniq = uniqueId("turnstile_");
            this.el.classList.add(this.uniq);
            const selector = `.${this.uniq} .s_website_form_send,.${this.uniq} .o_website_form_send`;
            const btnEl = document.querySelector(selector);
            if (btnEl && !btnEl.classList.contains('disabled') && !btnEl.classList.contains('no_auto_disable')) {
                btnEl.classList.add('disabled', 'cf_form_disabled');
            }
            const [turnstileEl, script1El, script2El, input] = this.addTurnstile("website_form", selector);
            const formSendEl = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            formSendEl.parentNode.insertBefore(turnstileEl, formSendEl);
            formSendEl.parentNode.insertBefore(script1El, formSendEl.nextSibling);
            formSendEl.parentNode.insertBefore(script2El, formSendEl.nextSibling);
            formSendEl.parentNode.insertBefore(input, formSendEl.nextSibling);
        }
        return res;
    },
});

publicWidget.registry.turnstileCaptcha = publicWidget.Widget.extend({
    ...turnStile,

    selector: "form[data-captcha]",

    async willStart() {
        this._super(...arguments);
        this.cleanTurnstile();
        if (
            !this.isEditable &&
            !this.el.querySelector(".s_turnstile") &&
            session.turnstile_site_key
        ) {
            this.uniq = uniqueId("turnstile_");
            const action = this.el.dataset.captcha || "generic";

            const [turnstileEl, script1El, script2El, input] = this.addTurnstile(action, `.${this.uniq}`);
            const submitButton = this.el.querySelector("button[type='submit']");
            submitButton.classList.add(this.uniq);
            if (!submitButton.classList.contains('no_auto_disable')) {
                submitButton.classList.add('disabled', 'cf_form_disabled');
            }
            submitButton.parentNode.insertBefore(turnstileEl, submitButton);
            this.el.appendChild(script1El);
            this.el.appendChild(script2El);
            this.el.appendChild(input);
        }
    },
});
