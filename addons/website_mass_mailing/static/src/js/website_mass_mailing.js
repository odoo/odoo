odoo.define('mass_mailing.website_integration', function (require) {
"use strict";

var core = require('web.core');
var publicWidget = require('web.public.widget');
const {ReCaptcha} = require('google_recaptcha.ReCaptchaV3');

var _t = core._t;

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
        return Promise.all([def, this._rpc({
            route: '/website_mass_mailing/is_subscriber',
            params: {
                'list_id': this.$target.data('list-id'),
            },
        }).then(always).guardedCatch(always)]);
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
        const subscribeBtnEl = this.$target[0].querySelector('.js_subscribe_btn');
        const thanksBtnEl = this.$target[0].querySelector('.js_subscribed_btn');
        const emailInputEl = this.$target[0].querySelector('input.js_subscribe_email');

        subscribeBtnEl.disabled = isSubscriber;
        emailInputEl.value = data.email || '';
        emailInputEl.disabled = isSubscriber;
        // Compat: remove d-none for DBs that have the button saved with it.
        this.$target[0].classList.remove('d-none');

        subscribeBtnEl.classList.toggle('d-none', !!isSubscriber);
        thanksBtnEl.classList.toggle('d-none', !isSubscriber);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSubscribeClick: async function () {
        var self = this;
        var $email = this.$(".js_subscribe_email:visible");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            this.$target.addClass('o_has_error').find('.form-control').addClass('is-invalid');
            return false;
        }
        this.$target.removeClass('o_has_error').find('.form-control').removeClass('is-invalid');
        const tokenObj = await this._recaptcha.getToken('website_mass_mailing_subscribe');
        if (tokenObj.error) {
            self.displayNotification({
                type: 'danger',
                title: _t("Error"),
                message: tokenObj.error,
                sticky: true,
            });
            return false;
        }
        this._rpc({
            route: '/website_mass_mailing/subscribe',
            params: {
                'list_id': this.$target.data('list-id'),
                'email': $email.length ? $email.val() : false,
                recaptcha_token_response: tokenObj.token,
            },
        }).then(function (result) {
            let toastType = result.toast_type;
            if (toastType === 'success') {
                self.$(".js_subscribe_btn").addClass('d-none');
                self.$(".js_subscribed_btn").removeClass('d-none');
                self.$('input.js_subscribe_email').prop('disabled', !!result);
                const $popup = self.$target.closest('.o_newsletter_modal');
                if ($popup.length) {
                    $popup.modal('hide');
                }
            }
            self.displayNotification({
                type: toastType,
                title: toastType === 'success' ? _t('Success') : _t('Error'),
                message: result.toast_content,
                sticky: true,
            });
        });
    },
});
});
