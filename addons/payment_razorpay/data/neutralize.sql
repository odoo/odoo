-- disable razorpay payment provider
UPDATE payment_provider
   SET razorpay_key_id = NULL,
       razorpay_account_id = NULL,
       razorpay_access_token_expiry = NULL;
