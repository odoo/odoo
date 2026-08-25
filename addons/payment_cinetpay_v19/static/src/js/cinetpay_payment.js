/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

console.log("✅ CinetPay POS patch loaded");

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const selectedPaymentLine = this.paymentLines.at(-1); // Dernier paiement ajouté
        const order = this.currentOrder;

        if (
            selectedPaymentLine &&
            selectedPaymentLine.payment_method &&
            selectedPaymentLine.payment_method.name &&
            selectedPaymentLine.payment_method.name.toLowerCase().includes("cinetpay")
        ) {
            this.showPopup('ConfirmPopup', {
                title: 'Paiement CinetPay',
                body: 'Redirection vers CinetPay en cours...',
                confirmText: 'OK',
                cancelText: 'Annuler',
                onConfirm: async () => {
                    const amount = selectedPaymentLine.amount;
                    const client = order.get_partner();  // Optionnel
                    const client_id = client ? client.id : '';

                    // Préparer l'URL de redirection vers ton contrôleur Odoo
                    const redirect_url = `/payment/cinetpay/pos/pay?amount=${amount}&client_id=${client_id}`;

                    // Redirection réelle
                    window.location.href = redirect_url;
                },
                onCancel: () => {
                    // Rien à faire
                },
            });

            // Ne pas valider la commande dans POS tant que le paiement n'est pas confirmé
            return;
        }

        // Sinon, validation normale
        await super.validateOrder(isForceValidate);
    }
});
