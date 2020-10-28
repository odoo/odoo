odoo.define('mail/static/src/components/notification_alert/notification_alert.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class NotificationAlert extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const isMessagingInitialized = this.env.isMessagingInitialized();
            return {
                isMessagingInitialized,
                isNotificationBlocked: this.isNotificationBlocked,
                settingUrl: this.isNotificationBlocked ? this.settingUrl : false,
                settingPath: this.isNotificationBlocked ? this.settingPath : false,
            };
        });
    }

    mounted() {
        super.mounted();
        if (this.isNotificationBlocked && this.settingUrl) {
            const $clipboardBtn = $(this.el.querySelector('.o_NotificationAlert_urlClipboardButton')).tooltip({
                title: this.env._t("Copied!"),
                trigger: 'manual',
                placement: 'right',
            });
            const clipboard = new ClipboardJS($clipboardBtn[0], {
                text: () => this.settingUrl,
                container: this.el,
            });
            clipboard.on('success', () => {
                setTimeout(() => {
                    $clipboardBtn.tooltip('show');
                    setTimeout(() => $clipboardBtn.tooltip('hide'), 800);
                });
            });
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    get isNotificationBlocked() {
        if (!this.env.isMessagingInitialized()) {
            return false;
        }
        const windowNotification = this.env.browser.Notification;
        return (
            windowNotification &&
            windowNotification.permission !== "granted" &&
            !this.env.messaging.isNotificationPermissionDefault()
        );
    }
    /**
     * @returns {string}
     */
    get settingPath() {
        const isBrowserSafari = navigator.userAgent.includes('Safari') && navigator.userAgent.search('Chrome') < 0;
        return isBrowserSafari ? this.env._t("(path:Safari > Preferences > Website > Notifications)") : '';
    }
    /**
     * @returns {string|undefined}
     */
    get settingUrl() {
        if (navigator.userAgent.includes('Chrome')) {
            return "chrome://settings/content/siteDetails?site=https%3A%2F%2F" + window.location.host;
        } else if (navigator.userAgent.includes('Firefox')) {
            return "about:preferences#privacy";
        }
    }
}

Object.assign(NotificationAlert, {
    props: {},
    template: 'mail.NotificationAlert',
});

return NotificationAlert;

});
