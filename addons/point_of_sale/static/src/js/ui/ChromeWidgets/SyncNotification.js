/** @odoo-module alias=point_of_sale.SyncNotification **/

const { useState } = owl;
import PosComponent from 'point_of_sale.PosComponent';

/**
 * @emits 'click-sync-notification'
 */
class SyncNotification extends PosComponent {
    constructor() {
        super(...arguments);
        this.state = useState({ status: 'connected' });
    }
    /**
     * @param {'connected' | 'connecting' | 'disconnected' | 'error'} status
     */
    setSyncStatus(status) {
        this.state.status = status;
    }
}
SyncNotification.template = 'point_of_sale.SyncNotification';

export default SyncNotification;
