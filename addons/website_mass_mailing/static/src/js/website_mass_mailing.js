import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import {ReCaptcha} from "@google_recaptcha/js/recaptcha";
import { rpc } from "@web/core/network/rpc";

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
        this.notification = this.bindService("notification");
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
        return Promise.all([def, rpc('/website_mass_mailing/is_subscriber', {
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
     * @todo should probably be merged with _updateSubscribeControlsStatus
     * @param {Object} data
     */
    _updateView(data) {
        this._updateSubscribeControlsStatus(!!data.is_subscriber);

        // js_subscribe_email is kept by compatibility (it was the old name of js_subscribe_value)
        const valueInputEl = this.el.querySelector('input.js_subscribe_value, input.js_subscribe_email');
        valueInputEl.value = data.value || '';

        // Compat: remove d-none for DBs that have the button saved with it.
        this.el.classList.remove('d-none');
    },
    /**
     * Updates the visibility of the subscribe and subscribed buttons.
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

        // js_subscribe_email is kept by compatibility (it was the old name of js_subscribe_value)
        const valueInputEl = this.el.querySelector('input.js_subscribe_value, input.js_subscribe_email');
        valueInputEl.disabled = isSubscriber;
    },

    _getListId: function () {
        // TODO this should be improved: we currently have snippets (e.g. the
        // s_newsletter_block one) who relies on the fact the list-id is saved
        // on the snippet's main section, and ignores the one saved on the inner
        // form snippet. Some other (e.g. the s_newsletter_popup one) relies on
        // the ID of the inner form snippet. We should make it more consistent:
        // probably always relying on the inner form list-id? (upgrade...)
        return this.el.closest('section[data-list-id]')?.dataset.listId || this.el.dataset.listId;
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
        rpc('/website_mass_mailing/subscribe', {
            'list_id': this._getListId(),
            'value': $input.length ? $input.val() : false,
            'subscription_type': inputName,
            recaptcha_token_response: tokenObj.token,
        }).then(function (result) {
            let toastType = result.toast_type;
            if (toastType === 'success') {
                self._updateSubscribeControlsStatus(true);

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
