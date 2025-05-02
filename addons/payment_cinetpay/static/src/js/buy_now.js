document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('paymentForm');

    if (!form) {
        console.error("Formulaire de paiement non trouvé !");
        return;
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const site_id = "105892963";
        const apikey = "19410334446807b0344dbb11.64095609";

        const transaction_id = "TXN_" + Date.now();
        const amount = parseInt(document.getElementById('amount').value);

        const currency = "XOF";
        const customer_name = document.getElementById('customer_name').value;
        const customer_surname = document.getElementById('customer_surname').value;
        const customer_email = document.getElementById('customer_email').value;
        const customer_phone_number = document.getElementById('customer_phone_number').value;
        const customer_address = document.getElementById('customer_address').value;
        const customer_city = document.getElementById('customer_city').value || "Ouagadougou"; // Valeur par défaut
        const customer_country = "BF"; // Burkina Faso
        const customer_state = "BF"; 
        const customer_zip_code = "065100"; 
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
            notify_url: "https://mon-site.com/cinetpay/notify", // 🚨 mettre ton vrai site ici
            mode: 'PRODUCTION'
        });

        CinetPay.getCheckout(data)
            .then(response => {
                console.log("🎉 Transaction démarrée :", response);
                // Ici tu pourrais aussi détecter la réponse de succès et rediriger par exemple
            })
            .catch(error => {
                console.error("❌ Erreur pendant le paiement :", error);
                if (error.message) {
                    alert("Erreur de démarrage du paiement : " + error.message);
                }
            });
    });
});
