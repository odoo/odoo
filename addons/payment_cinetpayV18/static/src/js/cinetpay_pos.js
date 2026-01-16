odoo.define('payment_cinetpay.cinetpay_pos', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const { patch } = require("@web/core/utils/patch");
    console.log("hello word");
    patch(PaymentScreen.prototype, {
        async validateOrder(isForceValidate) {
            const selectedPayment = this.paymentLines.get_selected_payment_line();

            if (selectedPayment?.payment_method?.name === "CinetPay") {
                const client = this.currentOrder.get_partner();
                const total = this.currentOrder.get_total_with_tax();

                const cinetpayData = {
                    amount: total,
                    order_reference: this.currentOrder.name || "Commande POS",
                    customer_name: client?.name || "Client POS",
                    customer_email: client?.email || "inconnu@example.com",
                    customer_phone_number: client?.phone || "0000000000",
                };

                console.log("🧾 Données POS/CinetPay:", cinetpayData);

                this.triggerCinetPayCheckout(cinetpayData);

                return;
            }

            await super.validateOrder(isForceValidate);
        },

        triggerCinetPayCheckout(cinetpayData) {
            const site_id = "XXXX";
            const apikey = "YYYY";

            CinetPay.setConfig({
                apikey: apikey,
                site_id: site_id,
                notify_url: "https://ton-site.com/payment/cinetpay/pos/notify",
                mode: "TEST"
            });

            CinetPay.getCheckout({
                ...cinetpayData,
                transaction_id: "TXN_" + Date.now(),
                currency: "XOF",
                channels: "ALL",
                description: "Paiement POS Odoo",
                metadata: JSON.stringify(cinetpayData)
            })
            .then(() => {
                CinetPay.waitResponse((result) => {
                    if (result.status === "ACCEPTED") {
                        alert("✅ Paiement réussi !");
                        this.finalizeAfterPayment();
                    } else {
                        alert("❌ Paiement échoué !");
                        this.showPopup("ErrorPopup", {
                            title: "Échec du paiement",
                            body: "Le paiement via CinetPay a échoué ou a été annulé.",
                        });
                    }
                });
            })
            .catch((error) => {
                console.error("Erreur de paiement CinetPay:", error);
                this.showPopup("ErrorPopup", {
                    title: "Erreur de paiement",
                    body: error.message || "Une erreur est survenue.",
                });
            });
        },

        async finalizeAfterPayment() {
            await super.validateOrder(false);
        }
    });
});
