// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Component, proxy, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ConnectionLostError } from "@web/core/network/rpc";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

// res.partner additional identifier holding each privilege type's ID number
// (registered in this module's res_partner.py).
const PARTNER_IDENTIFIER_KEYS = { sc: "PH_SC_ID", pwd: "PH_PWD_ID" };

/**
 * ID holders whose discount privilege is applied on some line of ``order``,
 * in order of appearance (see pos.order.line._l10n_ph_get_holder_key).
 */
export function getAppliedHolders(order) {
    const holders = new Map();
    for (const line of order.lines) {
        const privilege = line.l10n_ph_discount_privilege_id;
        if (!privilege) {
            continue;
        }
        const key = JSON.stringify([privilege.id, line.l10n_ph_holder_partner_id?.id || false]);
        if (!holders.has(key)) {
            holders.set(key, {
                key,
                privilege,
                name: line.l10n_ph_holder_name,
                id_number: line.l10n_ph_holder_id_number,
            });
        }
    }
    return [...holders.values()];
}

export class L10nPhDiscountPrivilegesDialog extends Component {
    static template = "l10n_ph_pos.DiscountPrivilegesDialog";
    static components = { Dialog };
    props = useProps({
        order: t.instanceOf(PosOrder),
        line: t.instanceOf(PosOrderline).optional(),
        close: t.function(),
        getPayload: t.function().optional(),
    });

    setup() {
        this.pos = usePos();
        // A second tap while applying would split the regular share again.
        this.confirm = useAsyncLockedMethod(this.confirm.bind(this));
        const appliedHolders = getAppliedHolders(this.props.order);
        const line = this.props.line;
        const hasEligibleLines = line ? this.isLineEligible(line) : this.orderHasEligibleLines();
        this.state = proxy({
            // "review": the selected line (or the whole order) is already
            // privileged, show the BIR Customer Information on file (the
            // review the spec calls for) instead of walking back into
            // "configure" only to fail with "no more lines to apply on".
            step: hasEligibleLines || !appliedHolders.length ? "configure" : "review",
            // Apply on the whole order unless the cashier explicitly picks the
            // selected line: a line is selected as soon as one is added, so
            // targeting it implicitly would silently skip the rest of the order.
            target: "order",
            selected: {}, // privilege id (string) -> requested ID count
            // The guest count, when pos_restaurant is installed.
            numPersonsSharing: this.props.order.getCustomerCount?.() || 1,
            holders: [],
            draft: this.emptyDraft(),
            error: "",
            appliedHolders,
        });
    }

    // --- Data ---

    getPrivileges() {
        return this.pos.models["l10n_ph.discount.privilege"].getAll();
    }

    getTitle() {
        return this.getTargetLine()
            ? _t("Discount Privileges (Selected Item)")
            : _t("Discount Privileges");
    }

    getIdTypeLabel(privilegeId) {
        return (
            this.pos.models["l10n_ph.discount.privilege"].get(privilegeId)?.l10n_ph_id_type_label ||
            ""
        );
    }

    /**
     * Mirrors pos.order.line._l10n_ph_is_discount_privilege_eligible.
     */
    isLineEligible(line) {
        return (
            !line.l10n_ph_discount_privilege_id &&
            line.product_id?.type !== "combo" &&
            !line.combo_parent_id &&
            line.qty > 0 &&
            line.price_unit >= 0 &&
            !line.isTipLine() &&
            !line.isServiceFeeLine()
        );
    }

    orderHasEligibleLines() {
        return this.props.order.lines.some((line) => this.isLineEligible(line));
    }

    canTargetSelectedLine() {
        return Boolean(this.props.line) && this.isLineEligible(this.props.line);
    }

    getTargetLine() {
        return this.state.target === "line" && this.canTargetSelectedLine()
            ? this.props.line
            : null;
    }

    // --- Review ---

    applyMore() {
        this.state.target = "order";
        this.state.step = "configure";
    }

    // --- Step 1: configure ---

    setTarget(target) {
        this.state.target = target;
    }

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

    getTotalIdsPresented() {
        return Object.values(this.state.selected).reduce((sum, count) => sum + count, 0);
    }

    canProceedToCollect() {
        const total = this.getTotalIdsPresented();
        return total > 0 && this.state.numPersonsSharing >= total;
    }

    goToCollect() {
        this.state.error = "";
        if (!this.getTotalIdsPresented()) {
            this.state.error = _t(
                "Select at least one discount privilege and how many IDs are presented."
            );
            return;
        }
        if (this.state.numPersonsSharing < this.getTotalIdsPresented()) {
            this.state.error = _t(
                "The number of persons sharing must be at least the number of IDs presented."
            );
            return;
        }
        this.state.slots = this.buildSlots();
        this.state.holders = [];
        this.state.draft = this.emptyDraft();
        this.state.step = "collect";
    }

    buildSlots() {
        const slots = [];
        for (const privilege of this.getPrivileges()) {
            const count = this.state.selected[privilege.id] || 0;
            for (let i = 0; i < count; i++) {
                slots.push(privilege);
            }
        }
        return slots;
    }

    // --- Step 2: collect ID holder info, one slot at a time ---

    getCurrentSlotPrivilege() {
        return this.state.slots?.[this.state.holders.length];
    }

    isCollectDone() {
        return Boolean(this.state.slots) && this.state.holders.length >= this.state.slots.length;
    }

    emptyDraft() {
        return proxy({
            partner: null,
            is_present: true,
            representative_name: "",
            representative_id: "",
        });
    }

    /**
     * ID number of ``privilege``'s ID document among ``partner``'s additional
     * identifiers (mirrors l10n_ph.discount.privilege._l10n_ph_get_partner_id_number).
     */
    getPartnerIdNumber(partner, privilege) {
        return (
            partner?.additional_identifiers?.[PARTNER_IDENTIFIER_KEYS[privilege?.discount_type]] ||
            ""
        );
    }

    /**
     * Statutory (SC/PWD) privileges require the ID holder's ID number on
     * their contact; it is missing when this returns true.
     */
    isDraftIdNumberMissing() {
        const privilege = this.getCurrentSlotPrivilege();
        return (
            Boolean(this.state.draft.partner) &&
            privilege?.discount_type in PARTNER_IDENTIFIER_KEYS &&
            !this.getPartnerIdNumber(this.state.draft.partner, privilege)
        );
    }

    /**
     * A person can claim only one privilege on an order (see
     * pos.order._l10n_ph_check_one_privilege_per_holder): return the name of
     * the privilege ``partner`` already claims, if any.
     */
    getPartnerClaimedPrivilegeName(partner) {
        const holder = this.state.holders.find((holder) => holder.partner_id === partner.id);
        if (holder) {
            return this.pos.models["l10n_ph.discount.privilege"].get(holder.privilege_id)?.name;
        }
        const privilegedLine = this.props.order.lines.find(
            (line) =>
                line.l10n_ph_holder_partner_id?.id === partner.id &&
                line.l10n_ph_discount_privilege_id &&
                line.l10n_ph_discount_privilege_id.id !== this.getCurrentSlotPrivilege()?.id
        );
        return privilegedLine?.l10n_ph_discount_privilege_id.name;
    }

    setDraftPartner(partner) {
        const claimedPrivilegeName = this.getPartnerClaimedPrivilegeName(partner);
        if (claimedPrivilegeName) {
            this.state.error = _t(
                "%(partner)s already claims the %(privilege)s privilege: discount privileges can't be combined.",
                { partner: partner.name, privilege: claimedPrivilegeName }
            );
            return;
        }
        this.state.error = "";
        this.state.draft.partner = partner;
    }

    /**
     * Pick the ID holder among the contacts (or create one), without
     * changing the order's customer.
     */
    async selectDraftPartner() {
        const partner = await makeAwaitable(this.pos.dialog, PartnerList, {
            partner: this.state.draft.partner,
        });
        if (partner) {
            this.setDraftPartner(partner);
        }
    }

    /**
     * Open the ID holder's contact, e.g. to add their missing ID number.
     */
    async editDraftPartner() {
        const partner = await this.pos.editPartner(this.state.draft.partner);
        if (partner) {
            this.setDraftPartner(partner);
        }
    }

    isDraftValid() {
        const draft = this.state.draft;
        if (!draft.partner || this.isDraftIdNumberMissing()) {
            return false;
        }
        if (
            !draft.is_present &&
            (!draft.representative_name.trim() || !draft.representative_id.trim())
        ) {
            return false;
        }
        return true;
    }

    addHolder() {
        if (!this.isDraftValid()) {
            return;
        }
        const privilege = this.getCurrentSlotPrivilege();
        const draft = this.state.draft;
        this.state.holders.push({
            privilege_id: privilege.id,
            partner_id: draft.partner.id,
            representative_name: draft.is_present ? "" : draft.representative_name.trim(),
            representative_id: draft.is_present ? "" : draft.representative_id.trim(),
            // Only shown in the summary: the server takes them from the contact.
            name: draft.partner.name,
            id_number: this.getPartnerIdNumber(draft.partner, privilege),
        });
        this.state.draft = this.emptyDraft();
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
                this.state.error = _t(
                    "Could not save the order before applying the discount privilege."
                );
            }
            return;
        }
        try {
            await this.pos.l10nPhApplyDiscountPrivileges(
                order,
                this.state.holders,
                this.state.numPersonsSharing,
                this.getTargetLine()
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
