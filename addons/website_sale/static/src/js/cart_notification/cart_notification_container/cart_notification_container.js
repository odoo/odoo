import { Component, useEffect, useState } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";
import { ItemAddedNotification } from '@website_sale/js/cart_notification/item_added_notification/item_added_notification';
import { WarningNotification } from '@website_sale/js/cart_notification/warning_notification/warning_notification';

export class CartNotificationContainer extends Component {
    static components = { ItemAddedNotification, WarningNotification };
    static template = 'website_sale.CartNotificationContainer';
    static props = {
        notifications: Set,
    }

    setup() {
        this.state = useState({
            notifications: this.props.notifications,
            topOffset: 0,
        });
        this.website_menus = useService('website_menus');

        // Ensure the notification is never on top of any header.
        useEffect(
            () => {
                this._adaptToHeaderChange();
                const cleanup = this.website_menus.registerCallback(
                    this._adaptToHeaderChange.bind(this)
                );
                return cleanup;
            },
            () => []
        );
    }

    /**
     * Set the top position (in px) of the notification based on the navbar height.
     *
     * This prevents the notification from being shown in front of the navbar.
     */
    _adaptToHeaderChange() {
        let position = 0;

        for (const el of document.querySelectorAll('.o_top_fixed_element')) {
            const { height, top } = el.getBoundingClientRect()
            // Add the element’s visible height; top < 0 for the portion scrolled out
            position += height + top;
        }

        if (this.state.topOffset !== position) {
            this.state.topOffset = position;
        }
    }
}
