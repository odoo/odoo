import { Component, onMounted, onWillUnmount, proxy, signal } from '@odoo/owl';
import { useService } from "@web/core/utils/hooks";
import { ItemAddedNotification } from '@website_sale/js/cart_notification/item_added_notification/item_added_notification';
import { WarningNotification } from '@website_sale/js/cart_notification/warning_notification/warning_notification';

export class CartNotificationContainer extends Component {
    static components = { ItemAddedNotification, WarningNotification };
    static template = 'website_sale.CartNotificationContainer';
    static props = {
        notifications: Set,
    }
    notificationStackRef = signal.ref();

    setup() {
        this.state = proxy({
            notifications: this.props.notifications,
        });
        this.publicInteractions = useService("public.interactions");

        onMounted(() => {
            this.publicInteractions.startInteractions(this.notificationStackRef());
        });
        onWillUnmount(() => {
            this.publicInteractions.stopInteractions(this.notificationStackRef());
        });
    }
}
