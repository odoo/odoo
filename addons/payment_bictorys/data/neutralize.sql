-- Part of Odoo. See LICENSE file for full copyright and licensing details.

-- Neutralize the Bictorys payment provider by clearing sensitive credentials.
UPDATE payment_provider
   SET bictorys_secret_key = NULL,
       bictorys_webhook_secret = NULL
 WHERE code = 'bictorys';
