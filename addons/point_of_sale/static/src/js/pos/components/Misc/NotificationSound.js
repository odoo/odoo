/** @odoo-module alias=point_of_sale.NotificationSound **/

const { useState } = owl;
import PosComponent from 'point_of_sale.PosComponent';

class NotificationSound extends PosComponent {
    constructor() {
        super(...arguments);
        this.state = useState({ src: false });
    }
    playSound(name) {
        let src = false;
        if (name === 'error') {
            src = '/point_of_sale/static/src/sounds/error.wav';
        } else if (name === 'bell') {
            src = '/point_of_sale/static/src/sounds/bell.wav';
        }
        this.state.src = src;
    }
}
NotificationSound.template = 'point_of_sale.NotificationSound';

export default NotificationSound;
