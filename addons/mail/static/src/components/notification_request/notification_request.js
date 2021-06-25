/** @odoo-module **/

import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useStore } from '@mail/component_hooks/use_store/use_store';
import { PartnerImStatusIcon } from '@mail/components/partner_im_status_icon/partner_im_status_icon';

import { browser } from '@web/core/browser/browser';

const { Component } = owl;

const components = { PartnerImStatusIcon };

export class NotificationRequest extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            return {
                isDeviceSmall: this.env.services.messaging.messaging.device.isSmall,
                partnerRoot: this.env.services.messaging.messaging.partnerRoot
                    ? this.env.services.messaging.messaging.partnerRoot.__state
                    : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    getHeaderText() {
        return _.str.sprintf(
            this.env._t("%s has a request"),
            this.env.services.messaging.messaging.partnerRoot.nameOrDisplayName
        );
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Handle the response of the user when prompted whether push notifications
     * are granted or denied.
     *
     * @private
     * @param {string} value
     */
    _handleResponseNotificationPermission(value) {
        this.env.services.messaging.messaging.refreshIsNotificationPermissionDefault();
        if (value !== 'granted') {
            this.env.services['bus_service'].sendNotification({
                message: this.env._t("Odoo will not have the permission to send native notifications on this device."),
                title: this.env._t("Permission denied"),
            });
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        const def = browser.Notification && browser.Notification.requestPermission();
        if (def) {
            def.then(this._handleResponseNotificationPermission.bind(this));
        }
        if (!this.env.services.messaging.messaging.device.isSmall) {
            this.env.services.messaging.messaging.messagingMenu.close();
        }
    }

}

Object.assign(NotificationRequest, {
    components,
    props: {},
    template: 'mail.NotificationRequest',
});
