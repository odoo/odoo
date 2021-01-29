odoo.define('mass_mailing.website_integration', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
const dom = require('web.dom');
var Dialog = require('web.Dialog');
var utils = require('web.utils');
var publicWidget = require('web.public.widget');
const session = require('web.session');

// FIXME the 14.0 was released with this but without the google_recaptcha
// module being added as a dependency of the website_mass_mailing module. This
// is to be fixed in master of course but in stable, we'll have to use a
// workaround.
// const {ReCaptcha} = require('google_recaptcha.ReCaptchaV3');

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
        const ReCaptchaService = odoo.__DEBUG__.services['google_recaptcha.ReCaptchaV3'];
        this._recaptcha = ReCaptchaService && new ReCaptchaService.ReCaptcha() || null;
    },
    /**
     * @override
     */
    willStart: function () {
        if (this._recaptcha) {
            this._recaptcha.loadLibs();
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);

        if (!this._recaptcha && this.editableMode && session.is_admin) {
            this.displayNotification({
                type: 'info',
                message: _t("Do you want to install Google reCAPTCHA to secure your newsletter subscriptions?"),
                sticky: true,
                buttons: [{text: _t("Install now"), primary: true, click: async () => {
                    dom.addButtonLoadingEffect($('.o_notification .btn-primary')[0]);

                    const record = await this._rpc({
                        model: 'ir.module.module',
                        method: 'search_read',
                        domain: [['name', '=', 'google_recaptcha']],
                        fields: ['id'],
                        limit: 1,
                    });
                    await this._rpc({
                        model: 'ir.module.module',
                        method: 'button_immediate_install',
                        args: [[record[0]['id']]],
                    });

                    this.displayNotification({
                        type: 'info',
                        message: _t("Google reCAPTCHA is now installed! You can configure it from your website settings."),
                        sticky: true,
                        buttons: [{text: _t("Website settings"), primary: true, click: async () => {
                            window.open('/web#action=website.action_website_configuration', '_blank');
                        }}],
                    });
                }}],
            });
        }

        this.$popup = this.$target.closest('.o_newsletter_modal');
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
        let tokenObj = null;
        if (this._recaptcha) {
            tokenObj = await this._recaptcha.getToken('website_mass_mailing_subscribe');
            if (tokenObj.error) {
                self.displayNotification({
                    type: 'danger',
                    title: _t("Error"),
                    message: tokenObj.error,
                    sticky: true,
                });
                return false;
            }
        }
        const params = {
            'list_id': this.$target.data('list-id'),
            'email': $email.length ? $email.val() : false,
        };
        if (this._recaptcha) {
            params['recaptcha_token_response'] = tokenObj.token;
        }
        this._rpc({
            route: '/website_mass_mailing/subscribe',
            params: params,
        }).then(function (result) {
            let toastType = result.toast_type;
            if (toastType === 'success') {
                self.$(".js_subscribe_btn").addClass('d-none');
                self.$(".js_subscribed_btn").removeClass('d-none');
                self.$('input.js_subscribe_email').prop('disabled', !!result);
                if (self.$popup.length) {
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

    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        this.websiteID = this._getContext().website_id;
        this.listID = parseInt(this.$target.attr('data-list-id'));
        if (!this.listID || (utils.get_cookie(_.str.sprintf("newsletter-popup-%s-%s", this.listID, this.websiteID)) && !self.editableMode)) {
            return Promise.all(defs);
        }
        if (this.$target.data('content') && this.editableMode) {
            // To avoid losing user changes.
            this._dialogInit(this.$target.data('content'));
            this.$target.removeData('quick-open');
            this.massMailingPopup.open();
        } else {
            defs.push(this._rpc({
                route: '/website_mass_mailing/get_content',
                params: {
                    newsletter_id: self.listID,
                },
            }).then(function (data) {
                self._dialogInit(data.popup_content, data.email || '');
                if (!self.editableMode && !data.is_subscriber) {
                    if (config.device.isMobile) {
                        setTimeout(function () {
                            self._showBanner();
                        }, 5000);
                    } else {
                        $(document).on('mouseleave.open_popup_event', self._showBanner.bind(self));
                    }
                } else {
                    $(document).off('mouseleave.open_popup_event');
                }
                // show popup after choosing a newsletter
                if (self.$target.data('quick-open')) {
                    self.massMailingPopup.open();
                    self.$target.removeData('quick-open');
                }
            }));
        }

        return Promise.all(defs);
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.massMailingPopup) {
            this.massMailingPopup.close();
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {string} content
     * @private
     */
    _dialogInit: function (content, email) {
        var self = this;
        this.massMailingPopup = new Dialog(this, {
            technical: false,
            $content: $('<div/>').html(content),
            $parentNode: this.$target,
            backdrop: !this.editableMode,
            dialogClass: 'p-0' + (this.editableMode ? ' oe_structure oe_empty' : ''),
            renderFooter: false,
            size: 'medium',
        });
        this.massMailingPopup.opened().then(function () {
            var $modal = self.massMailingPopup.$modal;
            $modal.find('header button.close').on('mouseup', function (ev) {
                ev.stopPropagation();
            });
            $modal.addClass('o_newsletter_modal');
            $modal.find('.oe_structure').attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            $modal.find('.modal-dialog').addClass('modal-dialog-centered');
            $modal.find('.js_subscribe').data('list-id', self.listID)
                  .find('input.js_subscribe_email').val(email);
            self.trigger_up('widgets_start_request', {
                editableMode: self.editableMode,
                $target: $modal,
            });
        });
        this.massMailingPopup.on('closed', this, function () {
            var $modal = self.massMailingPopup.$modal;
            if ($modal) { // The dialog might have never been opened
                self.$el.data('content', $modal.find('.modal-body').html());
            }
        });
    },
    /**
     * @private
     */
    _showBanner: function () {
        this.massMailingPopup.open();
        utils.set_cookie(_.str.sprintf("newsletter-popup-%s-%s", this.listID, this.websiteID), true);
        $(document).off('mouseleave.open_popup_event');
    },
});
});
