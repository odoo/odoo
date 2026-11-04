// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { patch } from "@web/core/utils/patch";

// Patched in: the discount breakdown is rendered inside the order summary,
// above the taxes, and the summary has no extension point for extra rows.
patch(OrderDisplay.prototype, {
    l10nPhGetDiscountBreakdown() {
        const totals = new Map();
        for (const line of this.order.lines) {
            const privilege = line.l10n_ph_discount_privilege_id;
            if (!privilege) {
                continue;
            }
            const row = totals.get(privilege.id) || { privilege, amount: 0 };
            row.amount += line.l10n_ph_special_discount_amount || 0;
            totals.set(privilege.id, row);
        }
        return [...totals.values()];
    },
});
