/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { notificationService } from "@web/core/notifications/notification_service";
import { useService } from "@web/core/utils/hooks";

publicWidget.registry.newsletterSubscription = publicWidget.Widget.extend({
    selector: ".container-newsletter",
    disabledInEditableMode: false,
    events: {
        'click .btn-submit': '_onSubscribeClick',
        'keypress .input-email-submit': '_onEnterKey'
    },

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this._recaptcha = new ReCaptcha();
        // Get notification service from the registry
        this.notification = useService("notification");
    },

    /**
     * @override
     */
    willStart: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this._recaptcha.loadLibs()
        ]);
    },

    /**
     * Handle Enter key press on email input
     * @private
     */
    _onEnterKey: function (event) {
        if (event.which === 13) { // Enter key
            event.preventDefault();
            this._onSubscribeClick();
        }
    },

    /**
     * Validate email and handle subscription
     * @private
     */
    _onSubscribeClick: async function () {
        const $input = this.$('.input-email-submit');
        const email = $input.val().trim();

        // Email validation
        if (!email.match(/.+@.+/)) {
            this._showNotification(_t("Please enter a valid email address."), 'danger');
            $input.addClass('is-invalid');
            return false;
        }

        // Remove any previous error states
        $input.removeClass('is-invalid');

        try {
            // Get reCAPTCHA token
            const tokenObj = await this._recaptcha.getToken('website_mass_mailing_subscribe');

            if (tokenObj.error) {
                this._showNotification(tokenObj.error, 'danger');
                return false;
            }

            // Perform subscription RPC
            const result = await rpc('/website_mass_mailing/subscribe', {
                'list_id': 1, // You might want to make this dynamic
                'value': email,
                'subscription_type': 'email',
                'recaptcha_token_response': tokenObj.token,
            });

            // Handle subscription result
            const toastType = result.toast_type || 'danger';

            this._showNotification(result.toast_content, toastType);

            // If successful, disable input and potentially hide/show elements
            if (toastType === 'success') {
                $input.prop('disabled', true);
                this.$('.btn-submit').addClass('disabled');
            }

        } catch (error) {
            // Handle any unexpected errors
            this._showNotification(_t("An unexpected error occurred."), 'danger');
        }
    },

    /**
     * Show notification in UI
     * @private
     */
    _showNotification: function (message, type) {
        // Ensure we have a notification service
        if (!this.notificationService) {
            return;
        }

        // Add notification to UI
        this.notification.add({
            type: type, // 'success', 'danger', 'warning', 'info'
            message: message,
            title: type === 'success' ? _t('Success') : _t('Error'),
            sticky: false, // Set to true if you want the notification to stay until manually closed
            timeout: 5000 // Notification will disappear after 5 seconds
        });
    }
});

export default publicWidget.registry.newsletterSubscription;
