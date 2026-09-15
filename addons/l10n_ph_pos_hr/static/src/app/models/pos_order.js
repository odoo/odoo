// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (!this.pos?.isPhilippinesCompany()) {
            return;
        }
        this.l10n_ph_pending_audit_actions = vals.l10n_ph_pending_audit_actions || [];
    },

    addL10nPhPendingAuditAction(action) {
        if (!action?.action_uid || !this.l10n_ph_pending_audit_actions) {
            return;
        }
        this.l10n_ph_pending_audit_actions = [
            ...this.l10n_ph_pending_audit_actions.filter((a) => a.action_uid !== action.action_uid),
            action,
        ];
        this.markDirty();
    },

    removeL10nPhPendingAuditAction(actionUid) {
        if (!actionUid || !this.l10n_ph_pending_audit_actions) {
            return;
        }
        const filtered = this.l10n_ph_pending_audit_actions.filter(
            (a) => a.action_uid !== actionUid
        );
        if (filtered.length !== this.l10n_ph_pending_audit_actions.length) {
            this.l10n_ph_pending_audit_actions = filtered;
            this.markDirty();
        }
    },

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this.l10n_ph_pending_audit_actions) {
            data.l10n_ph_pending_audit_actions = this.l10n_ph_pending_audit_actions;
        }
        return data;
    },
});
