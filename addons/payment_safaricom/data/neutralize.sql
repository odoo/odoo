-- disable safaricom payment provider
UPDATE payment_provider
   SET safaricom_consumer_key = NULL,
       safaricom_consumer_secret = NULL,
       safaricom_passkey = NULL,
       safaricom_shortcode = NULL,
       safaricom_till_number = NULL,
       safaricom_access_token = NULL,
       safaricom_access_token_expiry = NULL
 WHERE code = 'safaricom';
