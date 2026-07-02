/* global Sha1 */
// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { L10nPhPosVoidLinePopup } from "@l10n_ph_pos/app/components/void_line_popup/void_line_popup";

patch(PosStore.prototype, {
    isPhilippinesCompany() {
        return this.company?.country_id?.code === "PH";
    },

    l10nPhSetPendingDecrease(line, oldQuantity) {
        this._l10nPhPending = { line, oldQuantity };
    },

    l10nPhClearPendingDecrease() {
        this._l10nPhPending = null;
    },

    async l10nPhFlushPendingDecrease() {
        const pending = this._l10nPhPending;
        this._l10nPhPending = null;
        if (!pending) {
            return false;
        }
        const { line, oldQuantity } = pending;
        const newQuantity = line.getQuantity();
        if (newQuantity >= oldQuantity) {
            return false;
        }
        if (newQuantity === 0) {
            line.setQuantity(oldQuantity, false);
            if (await this._l10nPhRequestAuditAction(line, "line_void")) {
                this.getOrder().removeOrderline(line);
                return true;
            }
            return false;
        }
        const deltaQuantity = oldQuantity - newQuantity;
        const lineNetAmount = oldQuantity
            ? (line.priceIncl / oldQuantity) * deltaQuantity
            : line.priceIncl;
        if (
            await this._l10nPhRequestAuditAction(line, "quantity_decrease", {
                quantity: deltaQuantity,
                old_quantity: oldQuantity,
                new_quantity: newQuantity,
                net_amount: lineNetAmount,
            })
        ) {
            return true;
        }
        line.setQuantity(oldQuantity, false);
        return false;
    },

    async _l10nPhRequestLineVoidWithQty(line, oldQuantity) {
        if (oldQuantity <= 0) {
            this.getOrder().removeOrderline(line);
            return;
        }
        if (line.getQuantity() !== oldQuantity) {
            line.setQuantity(oldQuantity, false);
        }
        if (await this._l10nPhRequestAuditAction(line, "line_void")) {
            this.getOrder().removeOrderline(line);
        }
    },

    _l10nPhGetCashierEmployeeId() {
        const cashier = this.getCashier?.();
        if (!cashier) {
            return null;
        }
        if (cashier._l10n_ph_cashier_employee_id) {
            return cashier._l10n_ph_cashier_employee_id;
        }
        if (cashier.model?.name === "hr.employee") {
            return cashier.id;
        }
        return cashier.employee_id?.id ?? cashier.employee_id?.[0] ?? null;
    },

    _l10nPhCashierAllowsSelfLineVoid() {
        const cashier = this.getCashier?.();
        if (cashier?._l10n_ph_pos_allow_self_line_void) {
            return true;
        }
        const empId = this._l10nPhGetCashierEmployeeId();
        if (!empId) {
            return false;
        }
        const employee = this.models["hr.employee"]?.get(empId);
        return Boolean(employee?._l10n_ph_pos_allow_self_line_void);
    },

    _l10nPhValidateVoidApprover(passcode) {
        const trimmedPasscode = (passcode || "").trim();
        if (!trimmedPasscode) {
            return { error: "invalid" };
        }
        const employees = this.models["hr.employee"];
        if (!employees) {
            return { error: "invalid" };
        }
        const passcodeHash = Sha1.hash(trimmedPasscode);
        const matches = employees.filter(
            (emp) => emp._role !== "minimal" && emp._pin === passcodeHash
        );
        if (matches.length !== 1) {
            return { error: matches.length > 1 ? "ambiguous" : "invalid" };
        }
        return { approverId: matches[0].id };
    },

    _l10nPhShowAuditActionError(error = "invalid") {
        const body =
            error === "ambiguous"
                ? _t("The passcode matches multiple employees. Please use unique employee PINs.")
                : _t("The passcode is invalid or the audit request could not be saved.");
        this.dialog.add(AlertDialog, { title: _t("Unable to save audit action"), body });
    },

    _l10nPhNotifyQueuedAuditAction(actionType) {
        if (actionType === "line_void") {
            this.config.l10n_ph_void_counter += 1;
        }
        this.notification?.add(
            _t(
                "The audit action was saved locally and will be synchronized once the connection is restored."
            ),
            { title: _t("Saved offline"), type: "info" }
        );
    },

    _l10nPhBuildAuditAction(line, actionType, payload, approverValidation) {
        const isDecrease = actionType === "quantity_decrease";
        const lineQty = line.getQuantity();
        const unitPriceIncl = lineQty ? line.priceIncl / lineQty : line.priceIncl;
        const order = this.getOrder();
        return {
            action_uid:
                crypto.randomUUID?.() ?? `l10n-ph-${Date.now()}-${Math.round(Math.random() * 1e9)}`,
            action_type: actionType,
            reason: payload.reason,
            transaction_date: order?.date_order,
            cashier_employee_id: this._l10nPhGetCashierEmployeeId(),
            cashier_user_id: this.getCashierUserId?.() || null,
            product_id: line.product_id.id,
            description: line.getFullProductName(),
            unit_price: unitPriceIncl,
            approver_id: approverValidation.approverId,
            quantity: isDecrease ? payload.quantity ?? lineQty : lineQty,
            old_quantity: isDecrease ? payload.old_quantity ?? lineQty : lineQty,
            new_quantity: isDecrease ? payload.new_quantity ?? 0 : 0,
            net_amount: isDecrease ? payload.net_amount ?? line.priceIncl : line.priceIncl,
        };
    },

    async _l10nPhRequestAuditAction(line, actionType, extraPayload = {}) {
        const allowSelf = this._l10nPhCashierAllowsSelfLineVoid();
        const order = this.getOrder();
        const payload = await makeAwaitable(this.dialog, L10nPhPosVoidLinePopup, {
            line,
            order,
            actionType,
            oldQuantity: extraPayload.old_quantity,
            newQuantity: extraPayload.new_quantity,
            requirePasscode: !allowSelf,
        });
        if (!payload) {
            return false;
        }
        let approverValidation;
        if (allowSelf) {
            approverValidation = { approverId: this._l10nPhGetCashierEmployeeId() };
        } else {
            approverValidation = this._l10nPhValidateVoidApprover(payload.passcode);
            if (approverValidation.error) {
                this._l10nPhShowAuditActionError(approverValidation.error);
                return false;
            }
        }

        const auditAction = this._l10nPhBuildAuditAction(
            line,
            actionType,
            { ...payload, ...extraPayload },
            approverValidation
        );

        try {
            const response = await this.data.call(
                "pos.session",
                "l10n_ph_log_order_line_action",
                [
                    [this.session.id],
                    { ...auditAction, passcode: allowSelf ? "" : payload.passcode ?? "" },
                ],
                {},
                true
            );
            if (!response) {
                order.addL10nPhPendingAuditAction(auditAction);
                this._l10nPhNotifyQueuedAuditAction(actionType);
                return true;
            }
            order.removeL10nPhPendingAuditAction(auditAction.action_uid);
            this.config.l10n_ph_void_counter = response.void_counter;
            return true;
        } catch {
            order.removeL10nPhPendingAuditAction(auditAction.action_uid);
            this._l10nPhShowAuditActionError();
            return false;
        }
    },

    async pay() {
        if (this.isPhilippinesCompany()) {
            await this.l10nPhFlushPendingDecrease();
        }
        return super.pay(...arguments);
    },

    async validateOrderFast() {
        if (this.isPhilippinesCompany()) {
            await this.l10nPhFlushPendingDecrease();
        }
        return super.validateOrderFast(...arguments);
    },

    selectOrderLine(order, line) {
        if (this.isPhilippinesCompany()) {
            this.l10nPhFlushPendingDecrease();
        }
        return super.selectOrderLine(...arguments);
    },

    setOrder(order) {
        if (this.isPhilippinesCompany()) {
            this.l10nPhFlushPendingDecrease();
        }
        return super.setOrder(...arguments);
    },
});
