/** @odoo-module **/

import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useStore } from '@mail/component_hooks/use_store/use_store';
import { PartnerImStatusIcon } from '@mail/components/partner_im_status_icon/partner_im_status_icon';

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
                isDeviceMobile: this.env.messaging.device.isMobile,
                partnerRoot: this.env.messaging.partnerRoot
                    ? this.env.messaging.partnerRoot.__state
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
            this.env.messaging.partnerRoot.nameOrDisplayName
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
        this.env.messaging.refreshIsNotificationPermissionDefault();
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
        const windowNotification = this.env.browser.Notification;
        const def = windowNotification && windowNotification.requestPermission();
        if (def) {
            def.then(this._handleResponseNotificationPermission.bind(this));
        }
        if (!this.env.messaging.device.isMobile) {
            this.env.messaging.messagingMenu.close();
        }
    }

}

Object.assign(NotificationRequest, {
    components,
    props: {},
    template: 'mail.NotificationRequest',
});
