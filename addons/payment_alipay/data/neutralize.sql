-- disable adyen payment provider
UPDATE payment_provider
   SET alipay_merchant_partner_id = NULL,
       alipay_md5_signature_key = NULL,
       alipay_seller_email = NULL;
