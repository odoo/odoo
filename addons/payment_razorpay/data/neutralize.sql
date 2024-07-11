-- disable razorpay payment provider
UPDATE payment_provider
   SET razorpay_key_id = NULL,
       razorpay_key_secret = NULL,
       razorpay_webhook_secret = NULL;
