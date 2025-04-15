-- disable mercado_pago payment provider
UPDATE payment_provider
   SET mercado_pago_access_token = NULL;
