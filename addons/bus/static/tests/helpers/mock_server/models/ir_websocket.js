/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'bus/models/ir_websocket', {
    /**
     * Simulates `_update_presence` on `ir.websocket`.
     *
     * @param inactivityPeriod
     * @param imStatusIdsByModel
     */
     _mockIrWebsocket__updatePresence(inactivityPeriod, imStatusIdsByModel) {
        const imStatusNotifications = this._mockIrWebsocket__getImStatus(imStatusIdsByModel);
        if (Object.keys(imStatusNotifications).length > 0) {
            this._mockBusBus__sendone(this.currentPartnerId, 'bus/im_status', imStatusNotifications);
        }
    },
    /**
     * Simulates `_get_im_status` on `ir.websocket`.
     *
     * @param {Object} imStatusIdsByModel
     * @param {Number[]|undefined} res.partner ids of res.partners whose im_status
     * should be monitored.
     */
    _mockIrWebsocket__getImStatus(imStatusIdsByModel) {
        const imStatus = {};
        const { 'res.partner': partnerIds } = imStatusIdsByModel;
        if (partnerIds) {
            imStatus['partners'] = this.mockSearchRead('res.partner', [[['id', 'in', partnerIds]]], { context: { 'active_test': false }, fields: ['im_status'] })
        }
        return imStatus;
    },
});
