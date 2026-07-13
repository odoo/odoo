import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import { session } from '@web/session';
import { ReCaptcha } from '@google_recaptcha/js/recaptcha';
import { isVisible } from "@html_editor/utils/dom_info";
import { redirect } from "@web/core/utils/urls";

export class Subscribe extends Interaction {
    static selector = '.js_subscribe';
    dynamicContent = {
        ".js_subscribe_btn": { "t-on-click": this.locked(this.onSubscribeClick, true) },
        ".js_subscribe_value": { "t-on-keydown": this.locked(this.onInputKeydown) },
    };

    setup() {
        this._recaptcha = new ReCaptcha();
        this.notification = this.services['notification'];
        if (session.turnstile_site_key) {
            const { TurnStile } = odoo.loader.modules.get(
                "@website_cf_turnstile/interactions/turnstile"
            );
            this._turnstile = new TurnStile("website_mass_mailing_subscribe");
        }
    }

    async willStart() {
        const inputName = this.el.querySelector('input').name;
        const data = await this.waitFor(rpc(
            '/website_mass_mailing/is_subscriber',
            { 'list_id': this._getListId(), 'subscription_type': inputName },
        ))
        this._updateView(data);
        await this._recaptcha.loadLibs();
    }

    destroy() {
        this._updateView({ is_subscriber: false, warn_missing_list: false });
    }

    /**
     * Modify the elements to have the view of a subscriber/non-subscriber.
     *
     * @todo should probably be merged with _updateSubscribeControlsStatus
     * @param {Object} data
     */
    _updateView(data) {
        if (data.warn_missing_list) {
            this.renderAt("website_mass_mailing.subscribeListMissingError", {
                position: "afterbegin",
                removeOnClean: true,
            });
        }

        this._updateSubscribeControlsStatus(!!data.is_subscriber);

        // js_subscribe_email is kept for compatibility (old name of js_subscribe_value)
        const valueInputEl = this.el.querySelector('input.js_subscribe_value, input.js_subscribe_email');
        valueInputEl.value = data.value || '';

        // Compat: remove d-none for DBs that have the button saved with it.
        this.el.classList.remove('d-none');
    }

    /**
     * Update the visibility of the subscribe and subscribed buttons.
     *
     * @param {boolean} isSubscriber
     */
    _updateSubscribeControlsStatus(isSubscriber) {
        const subscribeWrapEl = this.el.querySelector('.js_subscribe_wrap');
        const subscribeBtnEl = this.el.querySelector('.js_subscribe_btn');

        if (this.el.dataset.successMode !== "closePopup") {
            const thanksWrapEl = this.el.querySelector(".js_subscribed_wrap");
            thanksWrapEl.classList.toggle("d-none", !isSubscriber);
        }

        subscribeBtnEl.disabled = isSubscriber;
        subscribeWrapEl.classList.toggle('d-none', isSubscriber);

        // js_subscribe_email is kept for compatibility (old name of js_subscribe_value)
        const valueInputEl = this.el.querySelector('input.js_subscribe_value, input.js_subscribe_email');
        valueInputEl.disabled = isSubscriber;

        // When the website is in edit mode, window.top != window. We don't want turnstile to render during edit mode
        // and mess up the DOM and saving it.
        if (!isSubscriber && this._turnstile && window.top === window) {
            const turnstileEl = this._turnstile.turnstileEl;
            this._turnstile.constructor.disableSubmit(subscribeBtnEl);
            turnstileEl.classList.add('mt-3');
            this.el.appendChild(turnstileEl);
            this._turnstile.insertScripts(this.el);
            this._turnstile.render();
        }
    }

    _getListId() {
        // The newsletter-related options have been moved from the block level
        // to the form level. Therefore, the `data-list-id` attribute is now
        // available only on editing element i.e. `s_newsletter_subscribe_form`.
        return this.el.dataset.listId;
    }

    async onInputKeydown(ev) {
        if (ev.key === "Enter") {
            await this.onSubscribeClick();
        }
    }

    async onSubscribeClick() {
        const inputName = this.el.querySelector('input').name;
        // js_subscribe_email is kept for compatibility (old name of js_subscribe_value)
        const input = this.el.querySelector('.js_subscribe_value, .js_subscribe_email');
        if (inputName === 'email' && isVisible(input) && !input.value.match(/.+@.+/)) {
            this.el.classList.add('o_has_error');
            this.el.querySelector('.form-control').classList.add('is-invalid');
            return;
        }
        this.el.classList.remove('o_has_error');
        this.el.querySelector('.form-control').classList.remove('is-invalid');
        const tokenObj = await this.waitFor(this._recaptcha.getToken(
            'website_mass_mailing_subscribe'
        ));
        if (tokenObj.error) {
            this.notification.add(tokenObj.error, {
                type: 'danger',
                sticky: true,
            });
            return;
        }
        const result = await this.waitFor(rpc('/website_mass_mailing/subscribe', {
            'list_id': this._getListId(),
            'value': input?.value ?? false,
            'subscription_type': inputName,
            ...(tokenObj.token ? { recaptcha_token_response: tokenObj.token } : {}),
            turnstile_captcha: this.el.parentElement.querySelector('input[name="turnstile_captcha"]')?.value,
        }));
        const toastType = result.toast_type;
        if (toastType === "success") {
            const { successMode, successPage } = this.el.dataset;
            switch (successMode) {
                case "redirect":
                    successPage && redirect(successPage);
                    this._updateSubscribeControlsStatus(true);
                    break;
                case "closePopup": {
                    const modalEl = this.el.closest(".o_newsletter_modal");
                    modalEl && window.Modal.getOrCreateInstance(modalEl).hide();
                    break;
                }
                case "message":
                    this._updateSubscribeControlsStatus(true);
                    break;
            }
        }
        this.notification.add(result.toast_content, {
            type: toastType,
            sticky: true,
        });
    }
}

registry
    .category('public.interactions')
    .add('website_mass_mailing.subscribe', Subscribe);
