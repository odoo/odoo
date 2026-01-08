-- disable razorpay payment provider
UPDATE payment_provider
   SET razorpay_public_token = NULL,
       razorpay_refresh_token = NULL,
       razorpay_access_token = NULL,
       razorpay_access_token_expiry = NULL,
       razorpay_account_id = NULL;
