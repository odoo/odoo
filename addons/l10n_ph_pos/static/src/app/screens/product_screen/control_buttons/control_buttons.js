// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { L10nPhDiscountPrivilegesDialog } from "@l10n_ph_pos/app/components/discount_privileges_dialog/discount_privileges_dialog";

// Patched in: the Actions popup has no other extension point for an extra button.
patch(ControlButtons.prototype, {
    l10nPhShowDiscountPrivileges() {
        return this.pos.company?.country_id?.code === "PH" && !this.pos.getOrder()?.isRefund;
    },
    async clickDiscountPrivileges() {
        const order = this.pos.getOrder();
        const line = order.getSelectedOrderline();
        await makeAwaitable(this.pos.dialog, L10nPhDiscountPrivilegesDialog, { order, line });
    },
});
