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
        const data = await this.l10nPhCallOrder(order, "l10n_ph_apply_discount_privileges", [
            holders,
            numPersonsSharing,
            targetLine?.uuid || false,
        ]);
        return this.l10nPhConnectOrderData(order, await this.data.missingRecursive(data));
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
        const data = await this.l10nPhCallOrder(order, "l10n_ph_remove_discount_privilege", [
            line.uuid,
        ]);
        const result = this.l10nPhConnectOrderData(order, data);
        if (!order.getSelectedOrderline()) {
            this.selectOrderLine(order, order.getLastOrderline());
        }
        return result;
    },
    /**
     * Merge the records of ``order`` read from the server (see
     * pos.order._l10n_ph_read_pos_data) into the local store. The lines the
     * order no longer has server side, e.g. a share merged back into its
     * regular share, are dropped first: they would be left behind out of
     * their order's lines by the merge, and crash the order's prices.
     * @param {import("@point_of_sale/app/models/pos_order").PosOrder} order
     * @param {object} data
     */
    l10nPhConnectOrderData(order, data) {
        const serverLineIds = new Set(data["pos.order.line"].map((vals) => vals.id));
        // Lines never synced have no server id yet: they are not the server's to drop.
        const staleLines = order.lines.filter(
            (line) => typeof line.id === "number" && !serverLineIds.has(line.id)
        );
        for (const line of staleLines) {
            this.data.localDeleteCascade(line);
        }
        // As PosData.callRelated does.
        this.data.deviceSync?.dispatch?.(data);
        const result = this.data.models.connectNewData(data);
        this.data.synchronizeServerDataInIndexedDB(data);
        return result;
    },
    /**
     * Call ``method`` of ``order``'s server record. When the server never
     * answers, it may have applied the change all the same, and the local
     * order, still as before it, would be synced back over it by its next
     * edit: read the order from the server again in that case, and flag the
     * error (``l10nPhOrderUpToDate``) with whether that worked. An error the
     * server answered with is its change rolled back.
     * @param {import("@point_of_sale/app/models/pos_order").PosOrder} order
     * @param {string} method
     * @param {Array} args the arguments following the order's id
     */
    async l10nPhCallOrder(order, method, args) {
        try {
            return await this.data.call("pos.order", method, [[order.id], ...args]);
        } catch (error) {
            if (!error?.data) {
                try {
                    const data = await this.data.call(
                        "pos.order",
                        "l10n_ph_read_discount_privilege_data",
                        [[order.id]]
                    );
                    this.l10nPhConnectOrderData(order, data);
                    error.l10nPhOrderUpToDate = true;
                } catch {
                    error.l10nPhOrderUpToDate = false;
                }
            }
            throw error;
        }
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
