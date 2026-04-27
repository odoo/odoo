/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.appointmentForm.include({
    init: function () {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
        this.notification = this.bindService("notification");
        // dynamic get rather than import as we don't depend on this module
        if (session.turnstile_site_key) {
            const { turnStile } = odoo.loader.modules.get("@website_cf_turnstile/js/turnstile");
            this._turnstile = turnStile;
        }
    },

    willStart: async function () {
        this._recaptcha.loadLibs();
        this._addTurnstile(document.querySelector("form.appointment_submit_form"));
        return this._super(...arguments);
    },

    /**
     * add recaptcha before submitting
     *
     * @override
     */
    _onConfirmAppointment: async function (ev) {
        const superFunc = this._super.bind(this);
        const button = ev.target;
        const form = button.closest("form");
        if (!(await this._addRecaptchaToken(form))) {
            button.setAttribute("disabled", true);
            setTimeout(() => button.removeAttribute("disabled"), 2000);
        } else {
            superFunc(...arguments);
        }
    },

    /**
     * Add an input containing the recaptcha token if relevant
     *
     * @returns {boolean} false if form submission should be cancelled otherwise true
     */
    _addRecaptchaToken: async function (form) {
        const tokenObj = await this._recaptcha.getToken("appointment_form_submission");
        if (tokenObj.error) {
            this.notification.add(tokenObj.error, {
                sticky: true,
                title: _t("Error"),
                type: "danger",
            });
            return false;
        } else if (tokenObj.token) {
            const recaptchaTokenInput = document.createElement("input");
            recaptchaTokenInput.setAttribute("name", "recaptcha_token_response");
            recaptchaTokenInput.setAttribute("type", "hidden");
            recaptchaTokenInput.setAttribute("value", tokenObj.token);
            form.appendChild(recaptchaTokenInput);
        }
        return true;
    },

    _addTurnstile: function (form) {
        if (!this._turnstile) {
            return false;
        }

        const turnstileNodes = this._turnstile.addTurnstile("appointment_form_submission");
        const turnstileContainer =
            turnstileNodes[0].classList.contains("s_turnstile_container") && turnstileNodes[0];
        turnstileContainer.classList.remove("float-end");
        turnstileContainer.classList.add("float-start");

        const submitButton = form.querySelector("button.o_appointment_form_confirm_btn");
        this._turnstile.addSpinnerNoMangle(submitButton);
        turnstileNodes.insertAfter(submitButton);
        this._turnstile.renderTurnstile(turnstileNodes);

        return true;
    },
});
