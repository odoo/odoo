import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class Subscribe extends Interaction {
    static selector = ".js_subscribe";
    dynamicContent = {
        ".js_subscribe_btn": {
            "t-on-click": this.onClickSubscribe,
            "t-att-disabled": () => this.isSubscriber,
        },
        _root: {
            "t-att-class": () => ({
                "d-none": false,
                "o_has_error": this.hasError,
            }),
        },
        ".form-control": {
            "t-att-class": () => ({ "is-invalid": this.hasError }),
        },
        ".js_subscribed_wrap": {
            "t-att-class": () => ({ "d-none": !this.isSubscriber }),
        },
        ".js_subscribe_wrap": {
            "t-att-class": () => ({ "d-none": this.isSubscriber }),
        },
        "input.js_subscribe_value, input.js_subscribe_email": {
            "t-att-disabled": () => this.isSubscriber,
            "t-att-value": () => this.subscribeValue,
        },
    };

    setup() {
        this.hasError = false;
        this.isSubscriber = false;
        this.subscribeValue = "";
        this.recaptcha = new ReCaptcha();
    }

    async willStart() {
        const res = await Promise.all([
            this.recaptcha.loadLibs(),
            rpc("/website_mass_mailing/is_subscriber", {
                "list_id": this.getListId(),
                "subscription_type": this.el.querySelector("input").name,
            }),
        ]);
        this.isSubscriber = res[1].is_subscriber;
        this.subscribeValue = res[1].value || '';
    }

    getListId() {
        // TODO this should be improved: we currently have snippets (e.g. the
        // s_newsletter_block one) who relies on the fact the list-id is saved
        // on the snippet's main section, and ignores the one saved on the inner
        // form snippet. Some other (e.g. the s_newsletter_popup one) relies on
        // the ID of the inner form snippet. We should make it more consistent:
        // probably always relying on the inner form list-id? (upgrade...)
        return this.el.closest('section[data-list-id]')?.dataset.listId || this.el.dataset.listId;
    }

    async onClickSubscribe() {
        const inputName = this.el.querySelector("input").getAttribute("name");
        // js_subscribe_email is kept by compatibility (it was the old name of js_subscribe_value)
        const inputEl = this.el.querySelector(".js_subscribe_value:not(.d-none), .js_subscribe_email:not(.d-none)");
        if (inputName === "email" && inputEl && !inputEl.value.match(/.+@.+/)) {
            this.hasError = true;
            return;
        }
        this.hasError = false;
        const tokenObj = await this.waitFor(this.recaptcha.getToken("website_mass_mailing_subscribe"));
        if (tokenObj.error) {
            this.services.notification.add(tokenObj.error, {
                type: "danger",
                title: _t("Error"),
                sticky: true,
            });
            return;
        }
        const data = await this.waitFor(rpc("/website_mass_mailing/subscribe", {
            "list_id": this.getListId(),
            "value": (inputEl && inputEl.value) || false,
            "subscription_type": inputName,
            recaptcha_token_response: tokenObj.token,
        }));
        const toastType = data.toast_type;
        if (toastType === "success") {
            this.isSubscriber = true;
            const popupEl = this.el.closest(".o_newsletter_modal");
            if (popupEl) {
                window.Modal.getOrCreateInstance(popupEl).hide();
            }
        }
        this.services.notification.add(data.toast_content, {
            type: toastType,
            title: toastType === "success" ? _t("Success") : _t("Error"),
            sticky: true,
        });
    }
}

registry
    .category("public.interactions")
    .add("website_mass_mailing.subscribe", Subscribe);
