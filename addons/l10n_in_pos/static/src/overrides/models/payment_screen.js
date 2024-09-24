/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { companyStateDialog } from "@l10n_in_pos/company_state_dialog/company_state_dialog";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ShipLater } from "@l10n_in_pos/overrides/components/ship_later";

patch(PaymentScreen.prototype, {
    toggleIsToInvoice() {
        if (this.pos.company.country_id?.code === "IN" && !this.pos.company.state_id) {
            this.dialog.add(companyStateDialog);
            return;
        }
        return super.toggleIsToInvoice();
    },
    async toggleShippingDatePicker() {
        if (this.pos.company.country_id?.code === "IN") {
            if (!this.currentOrder.getShippingDate()) {
                this.dialog.add(ShipLater, {
                    title: _t("Select the shipping date"),
                    getPayload: (shippingDate, stateId) => {
                        this.currentOrder.setShippingDate(shippingDate);
                        this.currentOrder.setPlaceOfSupply(stateId);
                    },
                });
            } else {
                this.currentOrder.setShippingDate(false);
            }
        } else {
            return super.toggleShippingDatePicker();
        }
    },
    async validateOrder(isForceValidate) {
        if (this.pos.company.country_id?.code === "IN") {
            if (!this.pos.config.ship_later || this.isValid) {
                super.validateOrder(isForceValidate);
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Invoice Mandatory"),
                    body: _t("For Inter State Shipping Invoice is Mandatory"),
                });
            }
        } else {
            super.validateOrder();
        }
    },
    get isValid() {
        return (
            this.pos.company.state_id == this.currentOrder.l10n_in_state_id ||
            this.currentOrder.to_invoice
        );
    },
});
