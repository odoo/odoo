-- Part of Odoo. See LICENSE file for full copyright and licensing details.

UPDATE payment_provider
   SET qfpay_app_code = NULL,
       qfpay_app_key = NULL,
       qfpay_mchntid = NULL;
