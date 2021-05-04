/** @odoo-module alias=point_of_sale.Notification **/

const { useState } = owl;
import PosComponent from 'point_of_sale.PosComponent';

class Notification extends PosComponent {
    constructor() {
        super(...arguments);
        this.state = useState({ show: false, message: '' });
    }
    onClickToastNotification() {
        this.state.show = false;
        this.state.message = '';
    }
    showNotification(message, duration) {
        this.state.show = true;
        this.state.message = message;
        setTimeout(() => {
            this.state.show = false;
            this.state.message = '';
        }, duration || 1000);
    }
}
Notification.template = 'point_of_sale.Notification';

export default Notification;
