-- disable razorpay payment provider
UPDATE payment_provider
   SET razorpay_authorization_state = NULL,
       razorpay_public_token = NULL,
       razorpay_refresh_token = NULL,
       razorpay_access_token = NULL,
       razorpay_access_token_expiration = NULL,
       razorpay_account_id = NULL,
       razorpay_webhook_id = NULL;
