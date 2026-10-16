// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

// Numpad modes locked on privileged shares: their discount and price are
// their privilege's, and their quantity is pro-rated by headcount.
export const L10N_PH_PRIVILEGED_LOCKED_MODES = ["quantity", "discount", "price"];

patch(PosStore.prototype, {
    /**
     * Split ``order`` (or only its ``targetLine``) between its regular share
     * and one share per ID holder, server side (see
     * pos.order.l10n_ph_apply_discount_privileges), and merge the result.
     * @param {import("@point_of_sale/app/models/pos_order").PosOrder} order
     * @param {object[]} holders
     * @param {number} numPersonsSharing
     * @param {import("@point_of_sale/app/models/pos_order_line").PosOrderline} [targetLine]
     */
    async l10nPhApplyDiscountPrivileges(order, holders, numPersonsSharing, targetLine) {
        return this.data.callRelated(
            "pos.order",
            "l10n_ph_apply_discount_privileges",
            [[order.id], holders, numPersonsSharing, targetLine?.uuid || false],
            {},
            false,
            true
        );
    },
    /**
     * Undo the split of the ID holder share ``line``, server side (see
     * pos.order.l10n_ph_remove_discount_privilege), and merge the result:
     * its quantity goes back to the regular share it was split off, if any.
     * @param {import("@point_of_sale/app/models/pos_order").PosOrder} order
     * @param {import("@point_of_sale/app/models/pos_order_line").PosOrderline} line
     */
    async l10nPhRemoveDiscountPrivilege(order, line) {
        await this.syncAllOrders({ throw: true, orders: [order] });
        const data = await this.data.call("pos.order", "l10n_ph_remove_discount_privilege", [
            [order.id],
            line.uuid,
        ]);
        // Merged back into its regular share, i.e. deleted server side: drop
        // it before merging the order's records, which no longer include it,
        // or it would be left behind out of its order's lines.
        if (!data["pos.order.line"].some((vals) => vals.id === line.id)) {
            this.data.localDeleteCascade(line);
        }
        // As PosData.callRelated does.
        this.data.deviceSync?.dispatch && this.data.deviceSync.dispatch(data);
        const result = this.data.models.connectNewData(data);
        this.data.synchronizeServerDataInIndexedDB(data);
        if (!order.getSelectedOrderline()) {
            this.selectOrderLine(order, order.getLastOrderline());
        }
        return result;
    },
    async setDiscountFromUI(line, val) {
        // No double discounting: a privileged share is discounted by its
        // privilege only.
        if (line.l10n_ph_discount_privilege_id) {
            return;
        }
        return super.setDiscountFromUI(line, val);
    },
});
