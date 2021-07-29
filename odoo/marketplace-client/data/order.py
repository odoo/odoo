def generate_pharmacy_order_request(buyer_id, seller_id, payment_method, special_notes):
    return {
        "detailsBuyer": [
            {
                "entityId": buyer_id
            }
        ],
        "detailsSeller": [
            {
                "entityId": seller_id,
                "paymentMethodId": payment_method,
                "note": special_notes
            }
        ]
    }
