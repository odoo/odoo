/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import {ReCaptcha} from "@google_recaptcha/js/recaptcha";

publicWidget.registry.subscribe = publicWidget.Widget.extend({
    selector: ".js_subscribe",
    disabledInEditableMode: false,
    read_events: {
        'click .js_subscribe_btn': '_onSubscribeClick',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
        this.rpc = this.bindService("rpc");
        this.notification = this.bindService("notification");
        if (session.turnstile_site_key) {
            const { turnStile } = odoo.loader.modules.get('@website_cf_turnstile/js/turnstile');
            this._turnstile = turnStile;
        }
    },
    /**
     * @override
     */
    willStart: function () {
        this._recaptcha.loadLibs();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        if (this.editableMode) {
            // Since there is an editor option to choose whether "Thanks" button
            // should be visible or not, we should not vary its visibility here.
            return def;
        }
        const always = this._updateView.bind(this);
        const inputName = this.el.querySelector('input').name;
        return Promise.all([def, this.rpc('/website_mass_mailing/is_subscriber', {
            'list_id': this._getListId(),
            'subscription_type': inputName,
        }).then(always, always)]);
    },
    /**
     * @override
     */
    destroy() {
        this._updateView({is_subscriber: false});
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Modifies the elements to have the view of a subscriber/non-subscriber.
     *
     * @param {Object} data
     */
    _updateView(data) {
        const isSubscriber = data.is_subscriber;
        const subscribeBtnEl = this.el.querySelector('.js_subscribe_btn');
        const thanksBtnEl = this.el.querySelector('.js_subscribed_btn');
        const valueInputEl = this.el.querySelector('input.js_subscribe_value, input.js_subscribe_email'); // js_subscribe_email is kept by compatibility (it was the old name of js_subscribe_value)

        subscribeBtnEl.disabled = isSubscriber;
        valueInputEl.value = data.value || '';
        valueInputEl.disabled = isSubscriber;
        // Compat: remove d-none for DBs that have the button saved with it.
        this.el.classList.remove('d-none');

        subscribeBtnEl.classList.toggle('d-none', !!isSubscriber);
        thanksBtnEl.classList.toggle('d-none', !isSubscriber);

        // When the website is in edit mode, window.top != window. We don't want turnstile to render during edit mode
        // and mess up the DOM and saving it.
        if (!isSubscriber && this._turnstile && window.top === window) {
            const el = this._turnstile.addTurnstile('website_mass_mailing_subscribe');
            if (el) {
                this._turnstile.addSpinner(subscribeBtnEl);
                el[0].classList.add('mt-3');
                el.insertAfter(this.el);
                this._turnstile.renderTurnstile(el);
            }
        }
    },

    _getListId: function () {
        return this.$el.closest('[data-snippet=s_newsletter_block').data('list-id') || this.$el.data('list-id');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSubscribeClick: async function () {
        var self = this;
        const inputName = this.$('input').attr('name');
        const $input = this.$(".js_subscribe_value:visible, .js_subscribe_email:visible"); // js_subscribe_email is kept by compatibility (it was the old name of js_subscribe_value)
        if (inputName === 'email' && $input.length && !$input.val().match(/.+@.+/)) {
            this.$el.addClass('o_has_error').find('.form-control').addClass('is-invalid');
            return false;
        }
        this.$el.removeClass('o_has_error').find('.form-control').removeClass('is-invalid');
        const tokenObj = await this._recaptcha.getToken('website_mass_mailing_subscribe');
        if (tokenObj.error) {
            self.notification.add(tokenObj.error, {
                type: 'danger',
                title: _t("Error"),
                sticky: true,
            });
            return false;
        }
        this.rpc('/website_mass_mailing/subscribe', {
            'list_id': this._getListId(),
            'value': $input.length ? $input.val() : false,
            'subscription_type': inputName,
            recaptcha_token_response: tokenObj.token,
            turnstile_captcha: this.el.parentElement.querySelector('input[name="turnstile_captcha"]')?.value,
        }).then(function (result) {
            let toastType = result.toast_type;
            if (toastType === 'success') {
                self.$(".js_subscribe_btn").addClass('d-none');
                self.$(".js_subscribed_btn").removeClass('d-none');
                self.$('input.js_subscribe_value, input.js_subscribe_email').prop('disabled', !!result); // js_subscribe_email is kept by compatibility (it was the old name of js_subscribe_value)
                const $popup = self.$el.closest('.o_newsletter_modal');
                if ($popup.length) {
                    $popup.modal('hide');
                }
            }
            self.notification.add(result.toast_content, {
                type: toastType,
                title: toastType === 'success' ? _t('Success') : _t('Error'),
                sticky: true,
            });
        });
    },
});

/**
 * This widget tries to fix snippets that were malformed because of a missing
 * upgrade script. Without this, some newsletter snippets coming from users
 * upgraded from a version lower than 16.0 may not be able to update their
 * newsletter block.
 *
 * TODO an upgrade script should be made to fix databases and get rid of this.
 */
publicWidget.registry.fixNewsletterListClass = publicWidget.Widget.extend({
    selector: '.s_newsletter_subscribe_form:not(.s_subscription_list), .s_newsletter_block',

    /**
     * @override
     */
    start() {
        this.$target[0].classList.add('s_newsletter_list');
        return this._super(...arguments);
    },
});
