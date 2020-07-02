odoo.define('mass_mailing.website_integration', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var utils = require('web.utils');
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
        var self = this;
        var def = this._super.apply(this, arguments);
        this.$popup = this.$target.closest('.modal');
        if (this.$popup.length) {
            // No need to check whether the user subscribed or not if the input
            // is in a popup as the popup won't open if he did subscribe.
            return def;
        }

        var always = function (data) {
            var isSubscriber = data.is_subscriber;
            self.$('.js_subscribe_btn').prop('disabled', isSubscriber);
            self.$('input.js_subscribe_email')
                .val(data.email || "")
                .prop('disabled', isSubscriber);
            // Compat: remove d-none for DBs that have the button saved with it.
            self.$target.removeClass('d-none');
            self.$('.js_subscribe_btn').toggleClass('d-none', !!isSubscriber);
            self.$('.js_subscribed_btn').toggleClass('d-none', !isSubscriber);
        };
        return Promise.all([def, this._rpc({
            route: '/website_mass_mailing/is_subscriber',
            params: {
                'list_id': this.$target.data('list-id'),
            },
        }).then(always).guardedCatch(always)]);
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
                if (self.$popup.length) {
                    self.$target.closest('.o_newsletter_popup').attr('data-subscribed', true);
                    self.$popup.modal('hide');
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

publicWidget.registry.newsletter_popup = publicWidget.Widget.extend({
    selector: ".o_newsletter_popup",
    disabledInEditableMode: false,
    events: {
        'hide.bs.modal': 'destroy',
    },

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        this.websiteID = this._getContext().website_id;
        this.listID = parseInt(this.$target.attr('data-list-id'));
        if (!this.listID || (utils.get_cookie(_.str.sprintf("newsletter-popup-%s-%s", this.listID, this.websiteID)) && !this.editableMode)) {
            return;
        }

        const $newsletterContent = this.$target.find(".o_newsletter_content");
        if (this.$target.data('content') && this.editableMode) {
            // To avoid losing user changes.
            $newsletterContent.html(this.$target.data('content'));
        } else {
            const data = await this._rpc({
                route: '/website_mass_mailing/get_content',
                params: {
                    newsletter_id: this.listID,
                },
            });
            $newsletterContent.html(data.popup_content);
            this.$target.find('.js_subscribe').attr('data-list-id', this.listID)
                  .find('input.js_subscribe_email').val(data.email);
            if (this.editableMode) {
                $newsletterContent.addClass('oe_structure oe_empty modal-body p-0')
                    .attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            }
        }
        this.trigger_up('widgets_start_request', {
            editableMode: this.editableMode,
            $target: $newsletterContent,
        });

    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$target.data('subscribed') === true){
            utils.set_cookie(_.str.sprintf("newsletter-popup-%s-%s", this.$target.attr('data-list-id'), this.websiteID), true)
        }
        if (parseInt(this.$el.attr('data-list-id')) === this.listID) {
            // To avoid losing user changes.
            this.$el.data('content', this.$target.find('.o_newsletter_content').html());
        }
        this._super.apply(this, arguments);
    },
});

publicWidget.registry.popup.include({
    /**
     * @override
     */
    start: function () {
        const newsletter_popup = this.$target.hasClass('o_newsletter_popup');
        let websiteID = this._getContext().website_id;
        let listID = parseInt(this.$target.attr('data-list-id'));
        // not open popup behaviour if a mailing list is subscribed by the user
        if (newsletter_popup && (!listID || (utils.get_cookie(_.str.sprintf("newsletter-popup-%s-%s", listID, websiteID)) && !this.editableMode))) {
            return;
        }
        return this._super(...arguments);
    },
});
});
