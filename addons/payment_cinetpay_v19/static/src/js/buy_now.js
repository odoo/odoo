document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('paymentForm');
    if (!form) {
        console.error("❌ Formulaire de paiement non trouvé !");
        return;
    }

    form.addEventListener('submit', handlePaymentSubmit);
});

function handlePaymentSubmit(e) {
    e.preventDefault();

    const cinetpayData = document.getElementById('cinetpay_data');
    if (!cinetpayData) {
        console.error("❌ Les données CinetPay sont manquantes !");
        alert("Erreur interne : données CinetPay introuvables.");
        return;
    }

    const site_id = cinetpayData.dataset.site_id;
    const apikey = cinetpayData.dataset.apikey;

    const amount = parseAmount();
    if (amount === null) return;

    const transaction_id = generateTransactionId();
    const order_reference = getValue('order_reference');
    const customerData = collectCustomerData();

    const data = {
        transaction_id: transaction_id,
        amount: amount,
        currency: "XOF",
        channels: "ALL",
        description: "Paiement de la commande : " + order_reference,
        ...customerData,
        metadata: "Commande " + order_reference
    };

    console.log("✅ Données envoyées à CinetPay : ", data);

    initCinetPay(site_id, apikey);
    startCinetPayCheckout(data);
}

function parseAmount() {
    const amountValue = parseInt(document.getElementById('amount').value);
    if (isNaN(amountValue) || amountValue <= 0) {
        alert("Montant invalide !");
        return null;
    }
    return amountValue;
}

function generateTransactionId() {
    return "TXN_" + Date.now();
}

function getValue(id, defaultValue = "") {
    const el = document.getElementById(id);
    return el ? el.value || defaultValue : defaultValue;
}

function collectCustomerData() {
    return {
        customer_name: getValue('customer_name'),
        customer_surname: getValue('customer_surname'),
        customer_email: getValue('customer_email'),
        customer_phone_number: getValue('customer_phone_number'),
        customer_address: getValue('customer_address'),
        customer_city: getValue('customer_city', "Ouagadougou"),
        customer_country: getValue('customer_country', "BF"),
        customer_state: getValue('customer_state', "KAD"),
        customer_zip_code: getValue('customer_zip', "0001")
    };
}

function initCinetPay(site_id, apikey) {
    CinetPay.setConfig({
        apikey: apikey,
        site_id: site_id,
        notify_url: "https://ton-site.com/cinetpay/notify", // 🔥 Mets ton URL réelle ici
        mode: 'TEST' // Change en 'PRODUCTION' quand tu es prêt
    });
}

function startCinetPayCheckout(data) {
    CinetPay.getCheckout(data)
        .then(response => {
            console.log("🎉 Transaction démarrée :", response);
            alert("Transaction démarrée ! Suivez les instructions sur la page.");

            // 👉 Ecoute la finalisation du paiement
            CinetPay.waitResponse(function (result) {
                console.log("📢 Résultat du paiement :", result);

                if (result.status === "ACCEPTED") {
                    alert("✅ Paiement réussi !");
                    window.location.href = "/payment/thank_you"; // Redirection après succès
                } else {
                    alert("❌ Paiement échoué ou annulé !");
                    window.location.href = "/payment/failed"; // Redirection après échec
                }
            });

        })
        .catch(error => {
            console.error("❌ Erreur pendant le paiement :", error);
            alert("Erreur de démarrage du paiement : " + (error.message || "Inconnue"));
        });
}
