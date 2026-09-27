-- disable razorpay payment provider
UPDATE payment_provider
   SET razorpay_key_id = NULL,
       razorpay_key_secret = NULL,
       razorpay_webhook_secret = NULL,
       razorpay_account_id = NULL,
       razorpay_refresh_token = NULL,
       razorpay_public_token = NULL,
       razorpay_access_token = NULL,
       razorpay_access_token_expiry = NULL;
