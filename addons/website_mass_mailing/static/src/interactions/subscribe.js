import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import { session } from '@web/session';
import { ReCaptcha } from '@google_recaptcha/js/recaptcha';
import { isVisible } from "@html_editor/utils/dom_info";

export class Subscribe extends Interaction {
    static selector = '.js_subscribe';
    dynamicContent = {
        '.js_subscribe_btn': { 't-on-click': this.onSubscribeClick },
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
        this._updateView({ is_subscriber: false });
    }

    /**
     * Modify the elements to have the view of a subscriber/non-subscriber.
     *
     * @todo should probably be merged with _updateSubscribeControlsStatus
     * @param {Object} data
     */
    _updateView(data) {
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
        const thanksWrapEl = this.el.querySelector('.js_subscribed_wrap');
        const subscribeWrapEl = this.el.querySelector('.js_subscribe_wrap');
        const subscribeBtnEl = this.el.querySelector('.js_subscribe_btn');

        subscribeBtnEl.disabled = isSubscriber;
        subscribeWrapEl.classList.toggle('d-none', isSubscriber);
        thanksWrapEl.classList.toggle('d-none', !isSubscriber);

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
        // TODO this should be improved: we currently have snippets (e.g. the
        // s_newsletter_block one) who relies on the fact the list-id is saved
        // on the snippet's main section, and ignores the one saved on the inner
        // form snippet. Some other (e.g. the s_newsletter_popup one) relies on
        // the ID of the inner form snippet. We should make it more consistent:
        // probably always relying on the inner form list-id? (upgrade...)
        return this.el.closest('section[data-list-id]')?.dataset.listId || this.el.dataset.listId;
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
        if (toastType === 'success') {
            this._updateSubscribeControlsStatus(true);
            const modalEl = this.el.closest('.o_newsletter_modal');
            if (modalEl) {
                window.Modal.getOrCreateInstance(modalEl).hide();
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
