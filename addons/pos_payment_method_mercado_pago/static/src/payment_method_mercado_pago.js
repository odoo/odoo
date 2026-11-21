import { usePlugin } from "@odoo/owl";
import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { _t } from "@web/core/l10n/translation";

class PaymentMethodMercadoPago extends PaymentMethod {
    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return true;
    }

    pollingIntervalMs() {
        return 5000;
    }

    setup() {
        super.setup(...arguments);
        this.dialog = usePlugin(DialogPlugin);
    }

    _mercadoPagoShowActionDialogIfRequired(response) {
        const isActionRequired =
            response.transaction_id in this.transactionCallbacks &&
            response.status === "pending" &&
            response.mercado_pago_status === "action_required";
        if (!isActionRequired) {
            this.closeDialog = null;
            return;
        }
        if (!this.closeDialog) {
            this.closeDialog = this.dialog.add(AlertDialog, {
                title: _t("Action Required"),
                body: _t("Complete the action on the Point device to continue."),
            });
        }
    }

    _handlePaymentResponse(response) {
        this._mercadoPagoShowActionDialogIfRequired(response);
        return super._handlePaymentResponse(...arguments);
    }

    async getTransactionStatus() {
        const response = await super.getTransactionStatus(...arguments);
        this._mercadoPagoShowActionDialogIfRequired(response);
        return response;
    }
}

electronicPaymentRegistry.add("mercado_pago", PaymentMethodMercadoPago);
