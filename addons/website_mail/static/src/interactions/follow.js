import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";

export class Follow extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".js_follow";
    dynamicContent = {
        ".js_follow > .d-none": {
            "t-att-class": () => ({ "d-none": false }),
        },
        ".js_follow_btn, .js_unfollow_btn": {
            "t-on-click.prevent.withTarget": this.onClick,
        },
    };

    setup() {
        this.isUser = false;
        this.recaptcha = new ReCaptcha();
    }

    async willStart() {
        const jsFollowEls = this.el.querySelectorAll(".js_follow");

        const records = {};
        for (const jsFollowEl of jsFollowEls) {
            const model = jsFollowEl.dataset.object;
            if (!(model in records)) {
                records[model] = [];
            }
            records[model].push(parseInt(jsFollowEl.dataset.id));
        }

        const promises = [
            rpc('/website_mail/is_follower', { records: records }),
            this.recaptcha.loadLibs(),
        ];
        const [data] = await this.waitFor(Promise.all(promises));

        this.isUser = data[0].is_user;
        for (const jsFollowEl of jsFollowEls) {
            const model = this.el.dataset.object;
            const email = data[0].email;
            const needToEnable = model in data[1] && data[1][model].includes(parseInt(this.el.dataset.id));
            this.toggleSubscription(needToEnable, email, jsFollowEl);
            jsFollowEl.classList.remove("d-none");
        }
    }

    /**
     * Toggles subscription state for every given records.
     *
     * @param {boolean} follow
     * @param {string} email
     * @param {HTMLElement} jsFollowEl
     */
    toggleSubscription(follow, email, jsFollowEl) {
        this.updateSubscriptionDOM(follow || !email && jsFollowEl.dataset.unsubscribe, email, jsFollowEl);
    }

    /**
     * Updates subscription DOM for every given records.
     * This should not be called directly, use `toggleSubscription`.
     *
     * @param {boolean} follow
     * @param {string} email
     * @param {HTMLElement} jsFollowEl
     */
    updateSubscriptionDOM(follow, email, jsFollowEl) {
        const jsFollowEmailEl = jsFollowEl.querySelector("input.js_follow_email");
        if (jsFollowEmailEl) {
            jsFollowEmailEl.setAttribute("value", email || "");
            if (email && (follow || this.isUser)) {
                jsFollowEmailEl.setAttribute("disabled", true)
            } else {
                jsFollowEmailEl.removeAttribute("disabled")
            }
        }
        jsFollowEl.dataset.follow = follow ? "on" : "off";
    }

    /**
     * @param {HTMLElement} jsFollowEl
     * @param {boolean} status
     */
    toggleEmailError(jsFollowEl, status) {
        jsFollowEl.classList.toggle('o_has_error', status)
        const formEls = jsFollowEl.querySelectorAll('.form-control, .form-select')
        for (const formEl of formEls) {
            formEl.classList.toggle('is-invalid', status);
        }
    }

    /**
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    async onClick(ev, currentTargetEl) {
        const jsFollowEl = currentTargetEl.closest(".js_follow");
        let email = jsFollowEl.querySelector(".js_follow_email");

        if (email && !/.+@.+/.test(email.value)) {
            this.toggleEmailError(jsFollowEl, true);
            return false;
        }

        this.toggleEmailError(jsFollowEl, false);
        email = email ? email.value : false;
        if (email || this.isUser) {
            const tokenCaptcha = await this.recaptcha.getToken("website_mail_follow");
            const token = tokenCaptcha.token;

            if (tokenCaptcha.error) {
                this.services.notification.add(tokenCaptcha.error, {
                    type: "danger",
                    title: _t("Error"),
                    sticky: true,
                });
                return false;
            }

            const turnstileCaptcha = document.querySelector("input[name='turnstile_captcha']");
            const turnstile = turnstileCaptcha ? turnstileCaptcha.value : "";
            
            const data = await this.waitFor(rpc("/website_mail/follow", {
                "id": parseInt(jsFollowEl.dataset.id),
                "object": jsFollowEl.dataset.object,
                "message_is_follower": jsFollowEl.dataset.follow || "off",
                "email": email,
                "recaptcha_token_response": token,
                "turnstile_captcha": turnstile,
            }));

            this.toggleSubscription(data, email, jsFollowEl);
        }

    }
}

registry
    .category("public.interactions")
    .add("website_mail.follow", Follow);
