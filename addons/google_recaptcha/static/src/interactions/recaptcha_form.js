/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { addLoadingEffect } from "@web/core/utils/ui";

export class RecaptchaForm extends Interaction {
    static selector = "form[data-captcha]";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
    };

    setup() {
        this.recaptcha = new ReCaptcha();
    }

    async willStart() {
        await this.recaptcha.loadLibs();
    }

    /**
     * @param {MouseEvent} ev
     */
    async onSubmit(ev) {
        const submitEl = this.el.querySelector("button[type='submit']");
        if (!submitEl.disabled) {
            addLoadingEffect(submitEl);
        }
        if (!this.el.querySelector("input[name='recaptcha_token_response']")) {
            ev.preventDefault();
            if (!submitEl.disabled) {
                addLoadingEffect(submitEl);
            }
            const action = this.el.dataset.captcha || "generic";
            const tokenCaptcha = await this.waitFor(this.recaptcha.getToken(action));
            if (tokenCaptcha.token) {
                // Do not send an 'undefined' value when reCAPTCHA is disabled
                // or not configured.
                const inputEl = document.createElement("input");
                inputEl.name = "recaptcha_token_response";
                inputEl.type = "hidden";
                inputEl.value = tokenCaptcha.token;
                this.insert(inputEl);
            }
            this.el.submit();
        }
    }
}

registry
    .category("public.interactions")
    .add("google_recaptcha.recaptcha_form", RecaptchaForm);
