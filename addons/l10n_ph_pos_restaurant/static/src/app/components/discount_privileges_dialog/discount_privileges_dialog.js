// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Component, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ConnectionLostError } from "@web/core/network/rpc";

export class L10nPhDiscountPrivilegesDialog extends Component {
    static template = "l10n_ph_pos_restaurant.DiscountPrivilegesDialog";
    static components = { Dialog };
    static props = {
        order: Object,
        line: { type: Object, optional: true },
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.state = proxy({
            step: "configure",
            selected: {}, // privilege id (string) -> requested ID count
            numPersonsSharing: this.props.order.getCustomerCount?.() || 1,
            holders: [],
            draft: this._emptyDraft(),
            error: "",
        });
    }

    // --- Data ---

    get privileges() {
        return this.pos.models["l10n_ph.discount.privilege"].getAll();
    }

    get title() {
        return this.props.line ? _t("Discount Privileges — Selected Item") : _t("Discount Privileges");
    }

    // --- Step 1: configure ---

    isSelected(privilege) {
        return Boolean(this.state.selected[privilege.id]);
    }

    toggleSelected(privilege) {
        if (this.isSelected(privilege)) {
            delete this.state.selected[privilege.id];
        } else {
            this.state.selected[privilege.id] = 1;
        }
    }

    setCount(privilege, value) {
        const count = Math.max(0, parseInt(value, 10) || 0);
        if (count === 0) {
            delete this.state.selected[privilege.id];
        } else {
            this.state.selected[privilege.id] = count;
        }
    }

    setNumPersonsSharing(value) {
        const parsed = parseInt(value, 10);
        if (parsed >= 1) {
            this.state.numPersonsSharing = parsed;
        }
    }

    get totalIdsPresented() {
        return Object.values(this.state.selected).reduce((sum, count) => sum + count, 0);
    }

    get canProceedToCollect() {
        return this.totalIdsPresented > 0 && this.state.numPersonsSharing >= this.totalIdsPresented;
    }

    goToCollect() {
        this.state.error = "";
        if (!this.totalIdsPresented) {
            this.state.error = _t("Select at least one discount privilege and how many IDs are presented.");
            return;
        }
        if (this.state.numPersonsSharing < this.totalIdsPresented) {
            this.state.error = _t("The number of persons sharing must be at least the number of IDs presented.");
            return;
        }
        this.state.slots = this._buildSlots();
        this.state.holders = [];
        this.state.draft = this._draftForSlot(this.state.slots[0]);
        this.state.step = "collect";
    }

    _buildSlots() {
        const slots = [];
        for (const privilege of this.privileges) {
            const count = this.state.selected[privilege.id] || 0;
            for (let i = 0; i < count; i++) {
                slots.push(privilege);
            }
        }
        return slots;
    }

    // --- Step 2: collect ID holder info, one slot at a time ---

    get currentSlotPrivilege() {
        return this.state.slots?.[this.state.holders.length];
    }

    get isCollectDone() {
        return Boolean(this.state.slots) && this.state.holders.length >= this.state.slots.length;
    }

    _emptyDraft() {
        return proxy({
            name: "",
            id_number: "",
            is_present: true,
            representative_name: "",
            representative_id: "",
            partner_id: false,
        });
    }

    /**
     * Prefill the draft from the order's customer when they're registered
     * under the slot's privilege type, so a frequent/regular diner's ID
     * doesn't need to be retyped every visit.
     */
    _draftForSlot(privilege) {
        const draft = this._emptyDraft();
        const partner = this.props.order.partner_id;
        if (privilege && partner?.l10n_ph_discount_privilege_id?.id === privilege.id) {
            draft.name = partner.name || "";
            draft.id_number = partner.l10n_ph_discount_privilege_id_number || "";
            draft.partner_id = partner.id;
        }
        return draft;
    }

    get isDraftValid() {
        const draft = this.state.draft;
        if (!draft.name.trim() || !draft.id_number.trim()) {
            return false;
        }
        if (!draft.is_present && (!draft.representative_name.trim() || !draft.representative_id.trim())) {
            return false;
        }
        return true;
    }

    addHolder() {
        if (!this.isDraftValid) {
            return;
        }
        const privilege = this.currentSlotPrivilege;
        const draft = this.state.draft;
        this.state.holders.push({
            privilege_id: privilege.id,
            name: draft.name.trim(),
            id_number: draft.id_number.trim(),
            is_present: draft.is_present,
            representative_name: draft.is_present ? "" : draft.representative_name.trim(),
            representative_id: draft.is_present ? "" : draft.representative_id.trim(),
            partner_id: draft.partner_id || false,
        });
        this.state.draft = this._draftForSlot(this.state.slots[this.state.holders.length]);
    }

    backToConfigure() {
        this.state.step = "configure";
        this.state.error = "";
    }

    // --- Confirm ---

    async confirm() {
        this.state.error = "";
        const order = this.props.order;
        try {
            await this.pos.syncAllOrders({ throw: true, orders: [order] });
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.state.error = _t(
                    "This requires an internet connection. Please try again once you're back online."
                );
            } else {
                this.state.error = _t("Could not save the order before applying the discount privilege.");
            }
            return;
        }
        try {
            await this.pos.data.callRelated(
                "pos.order",
                "l10n_ph_apply_discount_privileges",
                [[order.id], this.state.holders, this.state.numPersonsSharing, this.props.line?.uuid || false],
                {},
                false,
                true
            );
            this.props.close();
        } catch (error) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Could not apply the discount privilege"),
                body: error?.data?.message || error?.message || String(error),
            });
        }
    }
}
