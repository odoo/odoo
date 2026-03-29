/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { PosStore } from '@point_of_sale/app/store/pos_store';

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        console.log('[Bictorys] PosStore setup — connecting WebSocket BICTORYS_LATEST_RESPONSE');
        this.data.connectWebSocket('BICTORYS_LATEST_RESPONSE', () => {
            console.log('[Bictorys] WebSocket event received: BICTORYS_LATEST_RESPONSE');
            const pendingLine = this.getPendingPaymentLine('bictorys');
            console.log('[Bictorys] pending line:', pendingLine);
            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handleBictorysStatusResponse();
            }
        });
    },
});