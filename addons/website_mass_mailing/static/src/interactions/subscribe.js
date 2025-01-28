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
                "o_has_error": this.inError,
            }),
        },
        ".form-control": {
            "t-att-class": () => ({ "is-invalid": this.inError }),
        },
        ".js_subscribed_wrap": {
            "t-att-class": () => ({ "d-none": !this.isSubscriber }),
        },
        ".js_subscribe_wrap": {
            "t-att-class": () => ({ "d-none": this.isSubscriber }),
        },
        "input.js_subscribe_value, input.js_subscribe_email": {
            "t-att-disabled": () => this.isSubscriber,
            "t-att-value": () => "",
        },
    };

    setup() {
        this.inError = false;
        this.isSubscriber = false;
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
        this.isSubscriber = res[1];
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
        const inputEl = this.el.querySelector(".js_subscribe_value:visible, .js_subscribe_email:visible");
        if (inputName === "email" && inputEl && !inputEl.value.match(/.+@.+/)) {
            this.inError = true;
            return;
        }
        this.inError = false;
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

/**
* This interaction tries to fix snippets that were malformed because of a missing
* upgrade script. Without this, some newsletter snippets coming from users
* upgraded from a version lower than 16.0 may not be able to update their
* newsletter block.
*
* TODO an upgrade script should be made to fix databases and get rid of this.
*/

export class FixNewsletterListClasslist extends Interaction {
    static selector = ".s_newsletter_subscribe_form:not(.s_subscription_list), .s_newsletter_block";

    start() {
        this.el.classList.add("s_newsletter_list");
    }
}

registry
    .category("public.interactions")
    .add("website_mass_mailing.fix_newsletter_list_classlist", FixNewsletterListClasslist);
