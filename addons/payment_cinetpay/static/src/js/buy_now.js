document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('paymentForm');

    if (!form) {
        console.error("❌ Formulaire de paiement non trouvé !");
        return;
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const cinetpayData = document.getElementById('cinetpay_data');
        if (!cinetpayData) {
            console.error("❌ Les données CinetPay ne sont pas trouvées dans le HTML !");
            alert("Erreur interne : données CinetPay manquantes.");
            return;
        }

        const site_id = cinetpayData.dataset.site_id;
        const apikey = cinetpayData.dataset.apikey;

        const transaction_id = "TXN_" + Date.now();

        const amount = parseInt(document.getElementById('amount').value);
        if (isNaN(amount) || amount <= 0) {
            alert("Montant invalide !");
            return;
        }

        const currency = "XOF";
        const customer_name = document.getElementById('customer_name').value;
        const customer_surname = document.getElementById('customer_surname').value;
        const customer_email = document.getElementById('customer_email').value;
        const customer_phone_number = document.getElementById('customer_phone_number').value;
        const customer_address = document.getElementById('customer_address').value;
        const customer_city = document.getElementById('customer_city').value || "Ouagadougou";
        const customer_country = document.getElementById('customer_country').value || "BF";
        const customer_state = document.getElementById('customer_state').value || "KAD";
        const customer_zip_code = document.getElementById('customer_zip').value || "0001";
        const order_reference = document.getElementById('order_reference').value;
        const description = "Paiement de la commande : " + order_reference;

        const data = {
            transaction_id: transaction_id,
            amount: amount,
            currency: currency,
            channels: "ALL",
            description: description,
            customer_name: customer_name,
            customer_surname: customer_surname,
            customer_email: customer_email,
            customer_phone_number: customer_phone_number,
            customer_address: customer_address,
            customer_city: customer_city,
            customer_country: customer_country,
            customer_state: customer_state,
            customer_zip_code: customer_zip_code,
            metadata: "Commande " + order_reference
        };

        console.log("✅ Données envoyées à CinetPay : ", data);

        CinetPay.setConfig({
            apikey: apikey,
            site_id: site_id,
            notify_url: "https://ton-site.com/cinetpay/notify", // 🔥 Mets ton URL réelle ici
            mode: 'TEST' // Change en 'PRODUCTION' quand tu es prêt
        });

        CinetPay.getCheckout(data)
            .then(response => {
                console.log("🎉 Transaction démarrée :", response);
                alert("Transaction démarrée ! Suivez les instructions sur la page.");
            })
            .catch(error => {
                console.error("❌ Erreur pendant le paiement :", error);
                alert("Erreur de démarrage du paiement : " + (error.message || "Inconnue"));
            });
    });
});
