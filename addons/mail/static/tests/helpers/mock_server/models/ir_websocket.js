/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

// ensure bus override is applied first.
import "@bus/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/models/ir_websocket', {
    /**
     * Simulates `_get_im_status` on `ir.websocket`.
     *
     * @param {Object} imStatusIdsByModel
     * @param {Number[]|undefined} mail.guest ids of mail.guest whose im_status
     * should be monitored.
     */
    _mockIrWebsocket__getImStatus(imStatusIdsByModel) {
        const imStatus = this._super(imStatusIdsByModel);
        const { 'mail.guest': guestIds } = imStatusIdsByModel;
        if (guestIds) {
            imStatus['guests'] = this.pyEnv['mail.guest'].searchRead([['id', 'in', guestIds]], { context: { 'active_test': false }, fields: ['im_status'] });
        }
        return imStatus;
    },
});
